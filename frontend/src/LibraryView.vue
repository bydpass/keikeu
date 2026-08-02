<script setup>
import { computed, onActivated, onMounted, ref } from "vue";

import LibraryV4Projection from "./LibraryV4Projection.vue";
import { bridgeRequest, openSystemTarget } from "./bridge.js";

const props = defineProps({
  runtime: { type: Object, required: true },
  pendingIntent: { type: Object, default: null },
  request: { type: Function, default: bridgeRequest },
});
const emit = defineEmits([
  "runtime-blocked",
  "open-paper",
  "open-vault",
  "intent-settled",
]);

const view = ref(null);
const scope = ref("all");
const search = ref("");
const sort = ref("updated_desc");
const selectedPath = ref(null);
const moveDestination = ref("");
const folderName = ref("");
const renameValue = ref("");
const mergeDestination = ref("");
const busy = ref(false);
const notice = ref("");
const error = ref(null);
let generation = 0;

const entries = computed(() => view.value?.entries ?? []);
const selected = computed(
  () => entries.value.find((entry) => entry.path === selectedPath.value) ?? null,
);
const currentFolder = computed(() =>
  scope.value.startsWith("folder:") ? scope.value.slice(7) : null,
);
const currentTrashFolder = computed(() =>
  scope.value.startsWith("trash-folder:") ? scope.value.slice(13) : null,
);

function normalizeError(value) {
  return value && typeof value === "object"
    ? {
        code: value.code ?? "operation_failed",
        layer: value.layer ?? "vue_ui",
        message: value.message ?? "本地操作未完成。",
        recovery: value.recovery ?? "review",
      }
    : { code: "operation_failed", layer: "vue_ui", message: "本地操作未完成。", recovery: "review" };
}

function handleError(raw, fallback) {
  const normalized = normalizeError(raw);
  error.value = { ...normalized, message: `${fallback}：${normalized.message}` };
  if (["commit_unknown", "protocol_mismatch", "sidecar_unavailable"].includes(normalized.code)) {
    emit("runtime-blocked", error.value);
  }
}

function validateView(value) {
  if (
    !value || !Array.isArray(value.entries) || !Array.isArray(value.errors)
    || !Array.isArray(value.folders) || !Array.isArray(value.trash_folders)
    || typeof value.vault_locator !== "string"
    || !["current", "degraded"].includes(value.index_state)
  ) throw new Error("Library v4 projection is incomplete");
  return value;
}

async function refresh({ verify = false, preserveNotice = false } = {}) {
  const requestGeneration = ++generation;
  busy.value = true;
  error.value = null;
  if (!preserveNotice) notice.value = "";
  try {
    const result = validateView(await props.request("library.query", {
      scope: scope.value.startsWith("trash-folder:") ? "trash" : scope.value,
      search: search.value,
      sort: sort.value,
      verify_index: verify,
    }));
    if (requestGeneration !== generation) return;
    if (currentTrashFolder.value) {
      result.entries = result.entries.filter((entry) => entry.folder === currentTrashFolder.value);
    }
    view.value = result;
    if (!result.entries.some((entry) => entry.path === selectedPath.value)) {
      selectedPath.value = result.entries[0]?.path ?? null;
    }
  } catch (raw) {
    if (requestGeneration === generation) handleError(raw, "无法读取 Library");
  } finally {
    if (requestGeneration === generation) busy.value = false;
  }
}

function setScope(value) {
  scope.value = value;
  selectedPath.value = null;
  refresh();
}

function intent(method, params) {
  return {
    family: "library_path",
    method,
    vault_locator: view.value.vault_locator,
    summary: Object.fromEntries(
      Object.entries(params).filter(([key]) => key !== "vault_locator"),
    ),
  };
}

function reportsFrom(result) {
  if (Array.isArray(result?.reports)) return result.reports;
  if (result?.report) return [result.report];
  return [];
}

async function mutate(method, params, label) {
  if (busy.value || !view.value) return null;
  const complete = { ...params, vault_locator: view.value.vault_locator };
  busy.value = true;
  error.value = null;
  notice.value = "";
  try {
    const result = await props.request(method, complete, intent(method, complete));
    const reports = reportsFrom(result);
    const failed = reports.filter((item) => item.error);
    if (failed.length) {
      error.value = {
        code: "partial_result",
        layer: "application_service",
        message: failed.map((item) => `${item.source}：${item.error}`).join("；"),
        recovery: "review_failed_items",
      };
    }
    notice.value = reports.length
      ? `${label}：${reports.length - failed.length} 项成功，${failed.length} 项失败。`
      : `${label}完成${result?.name ? `：${result.name}` : ""}。`;
    if (result?.warnings?.includes("index_degraded")) {
      notice.value += " Index 需要显式重建。";
    }
    await refresh({ verify: true, preserveNotice: true });
    return result;
  } catch (raw) {
    handleError(raw, `无法${label}`);
    return null;
  } finally {
    busy.value = false;
  }
}

function openSelected() {
  if (selected.value && !selected.value.trashed) emit("open-paper", selected.value.path);
}

async function openExternally() {
  if (!selected.value || selected.value.trashed) return;
  try {
    await openSystemTarget("open", selected.value.path);
  } catch (raw) {
    handleError(raw, "无法交给默认编辑器");
  }
}

function branchSelected() {
  if (selected.value) mutate("library.branch", { path: selected.value.path }, "创建 Branch");
}

function moveSelected() {
  if (selected.value) mutate(
    "library.move",
    { paths: [selected.value.path], destination_folder: moveDestination.value || null },
    "移动 Paper",
  );
}

function deleteSelected() {
  if (selected.value) mutate("library.soft_delete", { paths: [selected.value.path] }, "移入废纸篓");
}

function restoreSelected() {
  if (selected.value) mutate("library.restore", { paths: [selected.value.path] }, "恢复 Paper");
}

function permanentlyDeleteSelected() {
  if (selected.value && window.confirm("永久删除这份 Paper？此操作不可撤销。")) {
    mutate("library.permanently_delete", { paths: [selected.value.path] }, "永久删除 Paper");
  }
}

async function createFolder() {
  const name = folderName.value.trim();
  if (!name) return;
  if (await mutate("library.create_folder", { name }, "创建文件夹")) folderName.value = "";
}

async function renameFolder() {
  if (!currentFolder.value || !renameValue.value.trim()) return;
  const result = await mutate(
    "library.rename_folder",
    { folder: currentFolder.value, new_name: renameValue.value.trim() },
    "重命名文件夹",
  );
  if (result?.name) scope.value = `folder:${result.name}`;
}

async function mergeFolder() {
  if (!currentFolder.value || !mergeDestination.value) return;
  await mutate(
    "library.merge_folders",
    { source: currentFolder.value, destination: mergeDestination.value },
    "合并文件夹",
  );
  scope.value = `folder:${mergeDestination.value}`;
  await refresh({ verify: true, preserveNotice: true });
}

async function deleteFolder() {
  if (!currentFolder.value || !window.confirm("将这个文件夹及其中 Paper 移入废纸篓？")) return;
  await mutate("library.soft_delete_folder", { folder: currentFolder.value }, "删除文件夹");
  scope.value = "all";
  await refresh({ verify: true, preserveNotice: true });
}

async function restoreFolder() {
  if (!currentTrashFolder.value) return;
  await mutate("library.restore_folder", { folder: currentTrashFolder.value }, "恢复文件夹");
  scope.value = "all";
  await refresh({ verify: true, preserveNotice: true });
}

async function permanentlyDeleteFolder() {
  if (!currentTrashFolder.value || !window.confirm("永久删除这个废纸篓文件夹？此操作不可撤销。")) return;
  await mutate("library.permanently_delete_folder", { folder: currentTrashFolder.value }, "永久删除文件夹");
  scope.value = "trash";
  await refresh({ verify: true, preserveNotice: true });
}

async function rebuildIndex() {
  await mutate("library.rebuild", {}, "重建 Index");
}

async function initialLoad() {
  const reconciling = props.pendingIntent?.family?.startsWith("library");
  await refresh({ verify: reconciling });
  if (reconciling && view.value) {
    notice.value = "已在重启后重新读取 Vault；请据磁盘结果确认上次操作。";
    emit("intent-settled");
  }
}

onMounted(initialLoad);
onActivated(() => { if (view.value) refresh(); });
</script>

<template>
  <main class="library-view">
    <header class="library-shell-header">
      <div>
        <p>KEIKEU · INDEX V4</p>
        <h1>Library</h1>
      </div>
      <nav>
        <button type="button" @click="emit('open-paper', null)">新 Paper</button>
        <button type="button" @click="emit('open-vault')">Vault</button>
      </nav>
    </header>

    <div v-if="view" class="library-shell">
      <aside class="library-scopes" aria-label="Library 范围">
        <button :class="{ selected: scope === 'all' }" @click="setScope('all')">全部 Paper</button>
        <button :class="{ selected: scope === 'unfiled' }" @click="setScope('unfiled')">未归档</button>
        <button
          v-for="folder in view.folders"
          :key="folder"
          :class="{ selected: scope === `folder:${folder}` }"
          @click="setScope(`folder:${folder}`)"
        >{{ folder }}</button>
        <button :class="{ selected: scope === 'trash' }" @click="setScope('trash')">
          废纸篓 · {{ view.trash_count }}
        </button>
        <button
          v-for="folder in view.trash_folders"
          :key="`trash-${folder}`"
          :class="{ selected: scope === `trash-folder:${folder}` }"
          @click="setScope(`trash-folder:${folder}`)"
        >↳ {{ folder }}</button>

        <section class="folder-create">
          <label>新文件夹<input v-model="folderName" placeholder="Ideas"></label>
          <button type="button" :disabled="busy || !folderName.trim()" @click="createFolder">创建</button>
        </section>
      </aside>

      <section class="library-main">
        <div class="library-toolbar">
          <label>排序
            <select v-model="sort" @change="refresh()">
              <option value="updated_desc">最近更新</option>
              <option value="name">名称</option>
              <option value="created_desc">最新创建</option>
              <option value="created_asc">最早创建</option>
            </select>
          </label>
          <span>{{ busy ? "正在读取…" : `${entries.length} 份 Paper` }}</span>
        </div>

        <p v-if="notice" class="library-notice" role="status">{{ notice }}</p>
        <p v-if="error" class="library-error" role="alert">{{ error.message }}</p>

        <LibraryV4Projection
          :entries="entries"
          :errors="view.errors"
          :index-state="view.index_state"
          :query="search"
          @search="search = $event; refresh()"
          @select="selectedPath = $event"
          @open="emit('open-paper', $event)"
          @rebuild-index="rebuildIndex"
        />

        <section v-if="selected" class="paper-operations" aria-label="所选 Paper 操作">
          <button v-if="!selected.trashed" type="button" @click="openSelected">编辑整份 Paper</button>
          <button v-if="!selected.trashed" type="button" @click="openExternally">默认编辑器打开</button>
          <button v-if="!selected.trashed" type="button" @click="branchSelected">创建 Branch</button>
          <template v-if="!selected.trashed">
            <select v-model="moveDestination" aria-label="目标文件夹">
              <option value="">未归档</option>
              <option v-for="folder in view.folders" :key="folder" :value="folder">{{ folder }}</option>
            </select>
            <button type="button" @click="moveSelected">移动</button>
            <button type="button" class="danger" @click="deleteSelected">移入废纸篓</button>
          </template>
          <template v-else>
            <button type="button" @click="restoreSelected">恢复</button>
            <button type="button" class="danger" @click="permanentlyDeleteSelected">永久删除</button>
          </template>
        </section>

        <section v-if="currentFolder" class="folder-operations" aria-label="当前文件夹操作">
          <label>新名称<input v-model="renameValue" :placeholder="currentFolder"></label>
          <button type="button" @click="renameFolder">重命名</button>
          <label>合并至
            <select v-model="mergeDestination">
              <option value="">选择文件夹</option>
              <option v-for="folder in view.folders.filter((item) => item !== currentFolder)" :key="folder" :value="folder">{{ folder }}</option>
            </select>
          </label>
          <button type="button" @click="mergeFolder">合并</button>
          <button type="button" class="danger" @click="deleteFolder">删除文件夹</button>
        </section>

        <section v-if="currentTrashFolder" class="folder-operations">
          <strong>废纸篓文件夹：{{ currentTrashFolder }}</strong>
          <button type="button" @click="restoreFolder">恢复文件夹</button>
          <button type="button" class="danger" @click="permanentlyDeleteFolder">永久删除文件夹</button>
        </section>
      </section>
    </div>

    <section v-else class="library-loading" aria-live="polite">
      <h2>{{ error ? error.message : "正在读取本地 Library…" }}</h2>
    </section>
  </main>
</template>

<style scoped>
.library-view { min-height: 100vh; padding: 26px clamp(18px, 4vw, 54px) 48px; }
.library-shell-header { display: flex; align-items: center; justify-content: space-between; max-width: 1180px; margin: 0 auto 20px; padding-bottom: 16px; border-bottom: 2px solid var(--ink); }
.library-shell-header p { margin: 0; color: var(--signal); font: 700 .68rem var(--font-mono); letter-spacing: .12em; }
.library-shell-header h1 { margin: 4px 0 0; font: 500 2.6rem var(--font-display); }
.library-shell-header nav, .paper-operations, .folder-operations { display: flex; flex-wrap: wrap; gap: 8px; }
button, input, select { min-height: 38px; padding: 7px 10px; border: 1px solid var(--rule); color: var(--ink); background: var(--paper); font: inherit; }
button { cursor: pointer; }
button:disabled { opacity: .5; cursor: wait; }
.library-shell { display: grid; grid-template-columns: 190px minmax(0, 1fr); gap: 34px; max-width: 1180px; margin: 0 auto; }
.library-scopes { display: grid; align-content: start; gap: 5px; }
.library-scopes > button { text-align: left; }
.library-scopes > button.selected { border-left: 4px solid var(--signal); background: var(--soft); }
.folder-create { display: grid; gap: 7px; margin-top: 18px; padding-top: 14px; border-top: 1px solid var(--rule); }
label { display: grid; gap: 5px; color: var(--muted); font-size: .72rem; font-weight: 700; }
.library-toolbar { display: flex; align-items: end; justify-content: space-between; margin-bottom: 8px; color: var(--meta); font-size: .75rem; }
.library-notice, .library-error { padding: 10px 14px; border-left: 4px solid var(--signal); background: var(--paper); }
.library-error { border-left-color: var(--danger); background: var(--danger-soft); }
.paper-operations, .folder-operations { margin-top: 16px; padding: 14px; border: 1px solid var(--rule); background: var(--soft); }
.danger { border-color: var(--danger); color: var(--danger); }
.library-loading { max-width: 720px; margin: 14vh auto; }
@media (max-width: 820px) { .library-shell { grid-template-columns: 1fr; } .library-scopes { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
@media (max-width: 620px) { .library-shell-header { align-items: flex-start; flex-direction: column; gap: 12px; } .library-scopes { grid-template-columns: 1fr; } }
</style>

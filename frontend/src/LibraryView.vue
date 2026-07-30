<script setup>
import {
  computed,
  nextTick,
  onActivated,
  onDeactivated,
  onMounted,
  onUnmounted,
  ref,
} from "vue";

import { bridgeRequest, openSystemTarget } from "./bridge.js";

defineProps({
  runtime: {
    type: Object,
    required: true,
  },
});

const emit = defineEmits([
  "runtime-blocked",
  "open-paper",
  "open-flashcard",
  "open-vault",
]);

const searchInput = ref(null);
const operationDialog = ref(null);
const view = ref(null);
const scope = ref("all");
const search = ref("");
const sort = ref("updated_desc");
const activePath = ref(null);
const selectedPaths = ref([]);
const busy = ref(false);
const queryError = ref(null);
const actionError = ref(null);
const notice = ref("");
const mutationBusy = ref(false);
const operation = ref(null);
const operationValue = ref("");
const operationDestination = ref("");
const draggedPath = ref(null);
let queryGeneration = 0;
let operationReturnFocus = null;
let activatedOnce = false;
let libraryActive = false;
let savedScrollY = 0;

const entries = computed(() => view.value?.entries ?? []);
const activeEntry = computed(
  () => entries.value.find((entry) => entry.path === activePath.value) ?? null,
);
const selectedCount = computed(() => selectedPaths.value.length);
const currentFolder = computed(() =>
  scope.value.startsWith("folder:") ? scope.value.slice(7) : null,
);
const operationCount = computed(() => operation.value?.paths?.length ?? 0);
const operationNeedsExecute = computed(
  () =>
    operation.value?.type.startsWith("permanent") &&
    operationCount.value >= 4,
);

function normalizeError(rawError) {
  if (rawError && typeof rawError === "object") {
    return {
      code: rawError.code ?? "operation_failed",
      layer: rawError.layer ?? "vue_ui",
      message: rawError.message ?? "本地操作未完成。",
      recovery: rawError.recovery ?? "review",
    };
  }
  return {
    code: "operation_failed",
    layer: "vue_ui",
    message: "本地操作未完成。",
    recovery: "review",
  };
}

function handleError(rawError, fallback, target) {
  const normalized = normalizeError(rawError);
  const visible = {
    ...normalized,
    message: `${fallback}：${normalized.message}`,
  };
  if (
    normalized.layer === "tauri_host" &&
    ["protocol_mismatch", "sidecar_unavailable", "commit_unknown"].includes(
      normalized.code,
    )
  ) {
    emit("runtime-blocked", visible);
    return true;
  }
  target.value = visible;
  return false;
}

function isNullableString(value) {
  return value === null || typeof value === "string";
}

function isStringArray(value) {
  return Array.isArray(value) && value.every((item) => typeof item === "string");
}

function validateView(nextView) {
  if (
    !nextView ||
    typeof nextView.scope !== "string" ||
    !Array.isArray(nextView.entries) ||
    !isStringArray(nextView.folders) ||
    !isStringArray(nextView.trash_folders) ||
    !Array.isArray(nextView.errors) ||
    !Number.isInteger(nextView.trash_count) ||
    nextView.trash_count < 0 ||
    nextView.entries.some(
      (entry) =>
        typeof entry?.path !== "string" ||
        typeof entry.code !== "string" ||
        !isNullableString(entry.display_name) ||
        !isNullableString(entry.folder) ||
        typeof entry.summary !== "string" ||
        !isStringArray(entry.tags) ||
        !isStringArray(entry.highlight_names) ||
        typeof entry.created !== "string" ||
        typeof entry.updated !== "string" ||
        typeof entry.trashed !== "boolean",
    ) ||
    nextView.errors.some(
      (item) =>
        typeof item?.path !== "string" || typeof item.reason !== "string",
    )
  ) {
    throw {
      code: "operation_failed",
      layer: "vue_ui",
      message: "Library 数据不完整。",
      recovery: "refresh",
    };
  }
  return nextView;
}

function clearSelection() {
  selectedPaths.value = [];
}

async function refresh({ clear = false, preserveNotice = false } = {}) {
  if (clear) {
    clearSelection();
    activePath.value = null;
  }
  const generation = ++queryGeneration;
  busy.value = true;
  queryError.value = null;
  if (!preserveNotice) {
    notice.value = "";
  }
  try {
    const result = validateView(
      await bridgeRequest("library.query", {
        scope: scope.value,
        search: search.value,
        sort: sort.value,
      }),
    );
    if (generation !== queryGeneration) {
      return;
    }
    view.value = result;
    scope.value = result.scope;
    if (!result.entries.some((entry) => entry.path === activePath.value)) {
      activePath.value = result.entries[0]?.path ?? null;
    }
  } catch (rawError) {
    if (generation === queryGeneration) {
      handleError(rawError, "无法读取 Library", queryError);
    }
  } finally {
    if (generation === queryGeneration) {
      busy.value = false;
    }
  }
}

function setScope(nextScope) {
  if (scope.value === nextScope) {
    return;
  }
  scope.value = nextScope;
  refresh({ clear: true });
}

function updateQuery() {
  refresh({ clear: true });
}

function toggleSelection(path, checked) {
  selectedPaths.value = checked
    ? [...new Set([...selectedPaths.value, path])]
    : selectedPaths.value.filter((selected) => selected !== path);
}

function selectAllVisible() {
  selectedPaths.value = entries.value.map((entry) => entry.path);
}

function activeReadablePath() {
  return activeEntry.value?.trashed ? null : activeEntry.value?.path ?? null;
}

function openPaper(path = activeReadablePath()) {
  savedScrollY = window.scrollY;
  emit("open-paper", path);
}

function openFlashcard(path = activeReadablePath()) {
  savedScrollY = window.scrollY;
  emit("open-flashcard", path);
}

function openVault() {
  savedScrollY = window.scrollY;
  emit("open-vault");
}

async function openOperation(type, { paths = [], folder = null } = {}) {
  operationReturnFocus = document.activeElement;
  operation.value = { type, paths: [...paths], folder };
  operationValue.value = type === "rename-folder" ? folder ?? "" : "";
  operationDestination.value = "";
  actionError.value = null;
  await nextTick();
  operationDialog.value?.focus();
}

function closeOperation() {
  if (!mutationBusy.value) {
    operation.value = null;
    nextTick(() => operationReturnFocus?.focus());
  }
}

function isOperationReport(value) {
  return (
    value &&
    typeof value.source === "string" &&
    isNullableString(value.destination) &&
    isNullableString(value.error)
  );
}

function reportRecords(value) {
  const records = Array.isArray(value) ? value : [value];
  if (!records.every(isOperationReport)) {
    throw {
      code: "operation_failed",
      layer: "vue_ui",
      message: "操作结果数据不完整。",
      recovery: "refresh",
    };
  }
  return records;
}

function recordReports(action, records) {
  const succeeded = records.filter((item) => item.error === null);
  const failed = records.filter((item) => item.error !== null);
  selectedPaths.value = selectedPaths.value.filter(
    (path) => !succeeded.some((item) => item.source === path),
  );
  notice.value = `${action}：${succeeded.length} 项成功，${failed.length} 项失败。`;
  if (failed.length > 0) {
    actionError.value = {
      code: "partial_result",
      layer: "application_service",
      message: failed
        .map((item) => `${item.source}：${item.error}`)
        .join("；"),
      recovery: "review_failed_items",
    };
  }
}

async function requestMutation(method, params, fallback) {
  mutationBusy.value = true;
  actionError.value = null;
  notice.value = "";
  try {
    return { ok: true, value: await bridgeRequest(method, params) };
  } catch (rawError) {
    const normalized = normalizeError(rawError);
    const fatal = handleError(rawError, fallback, actionError);
    if (
      !fatal &&
      ["stale_snapshot", "not_found", "conflict"].includes(normalized.code)
    ) {
      await refresh({ clear: true, preserveNotice: true });
    }
    return { ok: false, value: null };
  } finally {
    mutationBusy.value = false;
  }
}

async function runReportMutation(method, params, label) {
  const response = await requestMutation(method, params, `无法${label}`);
  if (!response.ok) {
    return false;
  }
  try {
    recordReports(label, reportRecords(response.value));
  } catch (rawError) {
    handleError(rawError, `无法确认${label}结果`, actionError);
    return false;
  }
  closeOperation();
  await refresh({ preserveNotice: true });
  return true;
}

async function runNamedMutation(method, params, label) {
  const response = await requestMutation(method, params, `无法${label}`);
  if (!response.ok) {
    return false;
  }
  if (typeof response.value !== "string") {
    handleError(
      {
        code: "operation_failed",
        layer: "vue_ui",
        message: "文件夹操作结果数据不完整。",
        recovery: "refresh",
      },
      `无法确认${label}结果`,
      actionError,
    );
    return false;
  }
  closeOperation();
  notice.value = `${label}：${response.value}`;
  await refresh({ clear: true, preserveNotice: true });
  return true;
}

async function rebuildLibrary() {
  const response = await requestMutation(
    "library.rebuild",
    { scope: scope.value, search: search.value, sort: sort.value },
    "无法重建索引",
  );
  if (!response.ok) {
    return;
  }
  try {
    queryGeneration += 1;
    view.value = validateView(response.value);
    scope.value = view.value.scope;
    clearSelection();
    activePath.value = view.value.entries[0]?.path ?? null;
    notice.value = "索引已从 Paper Markdown 重建。";
  } catch (rawError) {
    handleError(rawError, "无法确认索引重建结果", actionError);
  }
}

async function readAllTrash() {
  return validateView(
    await bridgeRequest("library.query", {
      scope: "trash",
      search: "",
      sort: sort.value,
    }),
  );
}

async function preparePermanentFolder(folder) {
  busy.value = true;
  actionError.value = null;
  try {
    const trash = await readAllTrash();
    openOperation("permanent-folder", {
      paths: trash.entries
        .filter((entry) => entry.folder === folder)
        .map((entry) => entry.path),
      folder,
    });
  } catch (rawError) {
    handleError(rawError, "无法读取 Trash 文件夹", actionError);
  } finally {
    busy.value = false;
  }
}

async function prepareClearTrash() {
  busy.value = true;
  actionError.value = null;
  try {
    const trash = await readAllTrash();
    openOperation("permanent-all", {
      paths: trash.entries.map((entry) => entry.path),
    });
    operation.value.folders = [...trash.trash_folders];
  } catch (rawError) {
    handleError(rawError, "无法读取完整 Trash", actionError);
  } finally {
    busy.value = false;
  }
}

async function permanentlyDelete(paths, folders, label) {
  const collected = [];
  if (paths.length > 0) {
    const papers = await requestMutation(
      "library.permanently_delete",
      { paths },
      `无法${label}`,
    );
    if (!papers.ok) {
      return;
    }
    const reports = reportRecords(papers.value);
    collected.push(...reports);
    if (reports.some((item) => item.error !== null)) {
      recordReports(label, collected);
      closeOperation();
      await refresh({ preserveNotice: true });
      return;
    }
  }
  for (const folder of folders) {
    const response = await requestMutation(
      "library.permanently_delete_folder",
      { folder },
      `无法永久删除文件夹 ${folder}`,
    );
    if (!response.ok) {
      if (collected.length > 0) {
        recordReports(label, collected);
        closeOperation();
        await refresh({ preserveNotice: true });
      }
      return;
    }
    collected.push(...reportRecords(response.value));
  }
  recordReports(label, collected);
  closeOperation();
  await refresh({ preserveNotice: true });
}

async function executeOperation() {
  if (!operation.value || mutationBusy.value) {
    return;
  }
  const current = operation.value;
  if (
    current.type.startsWith("permanent") &&
    operationNeedsExecute.value &&
    operationValue.value.trim() !== "execute"
  ) {
    actionError.value = {
      code: "validation_failed",
      layer: "vue_ui",
      message: "请输入完全一致的小写 execute。",
      recovery: "correct_input",
    };
    return;
  }
  if (current.type === "move") {
    await runReportMutation(
      "library.move",
      {
        paths: current.paths,
        destination_folder: operationDestination.value || null,
      },
      "移动",
    );
  } else if (current.type === "create-folder") {
    await runNamedMutation(
      "library.create_folder",
      { name: operationValue.value },
      "创建文件夹",
    );
  } else if (current.type === "rename-folder") {
    await runNamedMutation(
      "library.rename_folder",
      { folder: current.folder, new_name: operationValue.value },
      "重命名文件夹",
    );
  } else if (current.type === "merge-folder") {
    await runReportMutation(
      "library.merge_folders",
      { source: current.folder, destination: operationDestination.value },
      "合并文件夹",
    );
  } else if (current.type === "soft-delete") {
    await runReportMutation(
      "library.soft_delete",
      { paths: current.paths },
      "移至 Trash",
    );
  } else if (current.type === "soft-delete-folder") {
    await runReportMutation(
      "library.soft_delete_folder",
      { folder: current.folder },
      "文件夹移至 Trash",
    );
  } else if (current.type === "permanent-paper") {
    await permanentlyDelete(current.paths, [], "永久删除");
  } else if (current.type === "permanent-folder") {
    await permanentlyDelete(current.paths, [current.folder], "永久删除文件夹");
  } else if (current.type === "permanent-all") {
    await permanentlyDelete(
      current.paths,
      current.folders ?? [],
      "清空 Trash",
    );
  }
}

async function restorePaths(paths) {
  await runReportMutation("library.restore", { paths }, "恢复");
}

async function restoreFolder(folder) {
  await runReportMutation(
    "library.restore_folder",
    { folder },
    "恢复文件夹",
  );
}

async function branchActive() {
  if (activeEntry.value && !activeEntry.value.trashed) {
    await runReportMutation(
      "library.branch",
      { path: activeEntry.value.path },
      "创建分支",
    );
  }
}

function onDragStart(event, path) {
  draggedPath.value = path;
  event.dataTransfer?.setData("text/plain", path);
}

async function dropOnFolder(event, destinationFolder) {
  const path =
    event.dataTransfer?.getData("text/plain") || draggedPath.value;
  draggedPath.value = null;
  if (path) {
    await runReportMutation(
      "library.move",
      { paths: [path], destination_folder: destinationFolder },
      "移动",
    );
  }
}

async function runSystemAction(action, relativeTarget) {
  actionError.value = null;
  notice.value = "";
  try {
    await openSystemTarget(action, relativeTarget);
    notice.value =
      action === "open" ? "已交给系统打开文件。" : "已交给 Finder 显示位置。";
  } catch (rawError) {
    handleError(
      rawError,
      action === "open" ? "无法打开文件" : "无法在 Finder 中显示",
      actionError,
    );
  }
}

function onWindowKeydown(event) {
  if (event.key === "Escape" && operation.value) {
    event.preventDefault();
    closeOperation();
  } else if (
    !operation.value &&
    event.metaKey &&
    event.key.toLocaleLowerCase() === "f"
  ) {
    event.preventDefault();
    searchInput.value?.focus();
  } else if (event.key === "Escape" && selectedPaths.value.length > 0) {
    clearSelection();
  }
}

onMounted(() => {
  libraryActive = true;
  window.addEventListener("keydown", onWindowKeydown);
  refresh();
});

onActivated(async () => {
  libraryActive = true;
  window.addEventListener("keydown", onWindowKeydown);
  if (!activatedOnce) {
    activatedOnce = true;
    await nextTick();
    if (libraryActive) {
      window.scrollTo({ top: savedScrollY });
    }
    return;
  }
  await nextTick();
  if (libraryActive) {
    window.scrollTo({ top: savedScrollY });
  }
  await refresh();
  await nextTick();
  if (libraryActive) {
    window.scrollTo({ top: savedScrollY });
  }
});

onDeactivated(() => {
  libraryActive = false;
  queryGeneration += 1;
  window.removeEventListener("keydown", onWindowKeydown);
});

onUnmounted(() => {
  libraryActive = false;
  queryGeneration += 1;
  window.removeEventListener("keydown", onWindowKeydown);
});
</script>

<template>
  <main v-if="busy && !view" class="library-gate" aria-live="polite">
    <section>
      <p class="library-eyebrow">Road v0.5 · Library</p>
      <h1>正在读取 Library</h1>
      <p>搜索、排序与 scope 由 Python application service 执行。</p>
    </section>
  </main>

  <main v-else-if="!view" class="library-gate" aria-live="assertive">
    <section class="library-gate-error">
      <p class="library-eyebrow">Library 已阻塞</p>
      <h1>无法读取 Library</h1>
      <p>{{ queryError?.message ?? "本地索引暂时不可用。" }}</p>
      <button type="button" :disabled="busy" @click="refresh">
        {{ busy ? "正在重试…" : "重新读取" }}
      </button>
    </section>
  </main>

  <div v-else class="library-shell">
    <nav class="library-rail" aria-label="全局工作区">
      <span class="library-brand" aria-label="keikeu">K</span>
      <button
        class="library-destination"
        type="button"
        aria-label="打开 Paper"
        @click="openPaper()"
      >P<small>Paper</small></button>
      <button
        class="library-destination"
        type="button"
        aria-label="打开 Flashcard"
        @click="openFlashcard()"
      >F<small>Flash</small></button>
      <span class="library-destination is-active" aria-current="page">
        L<small>Library</small>
      </span>
      <span class="library-local">LOCAL</span>
    </nav>

    <aside class="library-context" aria-labelledby="library-scopes-title">
      <header>
        <p class="library-eyebrow">Road v0.5 · Library</p>
        <h1 id="library-scopes-title">Library</h1>
        <p>Python-owned mutations · {{ runtime.core_version }}</p>
      </header>

      <nav class="library-scopes" aria-label="Library scopes">
        <h2>Scopes</h2>
        <button
          type="button"
          :class="{ selected: scope === 'all' }"
          :disabled="mutationBusy"
          @click="setScope('all')"
        >全部 Paper</button>
        <button
          type="button"
          :class="{ selected: scope === 'unfiled' }"
          :disabled="mutationBusy"
          @dragover.prevent
          @drop.prevent="dropOnFolder($event, null)"
          @click="setScope('unfiled')"
        >未归类</button>
        <p v-if="view.folders.length" class="scope-label">文件夹</p>
        <button
          v-for="folder in view.folders"
          :key="folder"
          type="button"
          :class="{ selected: scope === `folder:${folder}` }"
          :disabled="mutationBusy"
          @dragover.prevent
          @drop.prevent="dropOnFolder($event, folder)"
          @click="setScope(`folder:${folder}`)"
        >{{ folder }}</button>
        <button
          type="button"
          :class="{ selected: scope === 'trash' }"
          :disabled="mutationBusy"
          @click="setScope('trash')"
        >Trash <span>{{ view.trash_count }}</span></button>
      </nav>

      <section v-if="currentFolder" class="folder-tools">
        <h2>文件夹操作</h2>
        <button
          type="button"
          :disabled="mutationBusy"
          @click="openOperation('rename-folder', { folder: currentFolder })"
        >重命名</button>
        <button
          type="button"
          :disabled="mutationBusy || view.folders.length < 2"
          @click="openOperation('merge-folder', { folder: currentFolder })"
        >合并到…</button>
        <button
          class="danger-action"
          type="button"
          :disabled="mutationBusy"
          @click="openOperation('soft-delete-folder', { folder: currentFolder })"
        >文件夹移至 Trash</button>
      </section>

      <section v-if="scope === 'trash' && view.trash_folders.length" class="trash-folders">
        <h2>Trash 文件夹</h2>
        <ul>
          <li v-for="folder in view.trash_folders" :key="folder">
            <span>{{ folder }}</span>
            <button
              type="button"
              :aria-label="`恢复文件夹 ${folder}`"
              :disabled="mutationBusy"
              @click="restoreFolder(folder)"
            >恢复</button>
            <button
              class="danger-action"
              type="button"
              :aria-label="`永久删除文件夹 ${folder}`"
              :disabled="mutationBusy"
              @click="preparePermanentFolder(folder)"
            >永久删除</button>
          </li>
        </ul>
      </section>

      <div class="vault-tools">
        <button
          class="reveal-vault"
          type="button"
          @click="runSystemAction('reveal', '.')"
        >在 Finder 中显示 Vault</button>
        <button type="button" :disabled="mutationBusy" @click="openVault">
          切换 Vault
        </button>
      </div>
    </aside>

    <main class="library-workspace">
      <header class="library-workspace-header">
        <div>
          <p class="library-eyebrow">Folder-aware retrieval</p>
          <h2>{{ scope === "all" ? "全部 Paper" : scope === "unfiled" ? "未归类" : scope === "trash" ? "Trash" : scope.slice(7) }}</h2>
        </div>
        <span>{{ entries.length }} 项 · 已选择 {{ selectedCount }}</span>
      </header>

      <form class="library-toolbar" @submit.prevent>
        <label>
          <span>搜索</span>
          <input
            ref="searchInput"
            v-model="search"
            type="search"
            :disabled="mutationBusy"
            placeholder="搜索名称、代号、摘要、标签或亮点"
            @input="updateQuery"
          >
          <small>⌘F</small>
        </label>
        <label>
          <span>排序</span>
          <select v-model="sort" :disabled="mutationBusy" @change="updateQuery">
            <option value="updated_desc">最近更新</option>
            <option value="created_desc">最近创建</option>
            <option value="created_asc">最早创建</option>
            <option value="name">名称</option>
          </select>
        </label>
        <button type="button" :disabled="busy || mutationBusy" @click="refresh({ clear: true })">
          {{ busy ? "读取中…" : "刷新" }}
        </button>
        <button type="button" :disabled="busy || mutationBusy" @click="rebuildLibrary">
          {{ mutationBusy ? "写入中…" : "重建索引" }}
        </button>
        <button
          type="button"
          :disabled="mutationBusy || scope === 'trash'"
          @click="openOperation('create-folder')"
        >新建文件夹</button>
      </form>

      <section v-if="queryError" class="library-error" aria-live="assertive">
        <strong>{{ queryError.message }}</strong>
        <small>{{ queryError.layer }} · {{ queryError.code }}</small>
      </section>

      <div class="library-stage">
        <section class="library-results" aria-labelledby="library-results-title">
          <header>
            <h3 id="library-results-title">结果</h3>
            <div>
              <button type="button" :disabled="entries.length === 0" @click="selectAllVisible">
                全选当前
              </button>
              <button type="button" :disabled="selectedCount === 0" @click="clearSelection">
                取消选择
              </button>
            </div>
          </header>

          <div class="mutation-toolbar">
            <template v-if="scope !== 'trash'">
              <button
                type="button"
                :disabled="mutationBusy || selectedCount === 0"
                @click="openOperation('move', { paths: [...selectedPaths] })"
              >移动所选</button>
              <button
                class="danger-action"
                type="button"
                :disabled="mutationBusy || selectedCount === 0"
                @click="openOperation('soft-delete', { paths: [...selectedPaths] })"
              >移至 Trash</button>
            </template>
            <template v-else>
              <button
                type="button"
                :disabled="mutationBusy || selectedCount === 0"
                @click="restorePaths([...selectedPaths])"
              >恢复所选</button>
              <button
                class="danger-action"
                type="button"
                :disabled="mutationBusy || selectedCount === 0"
                @click="openOperation('permanent-paper', { paths: [...selectedPaths] })"
              >永久删除所选</button>
              <button
                class="danger-action"
                type="button"
                :disabled="mutationBusy || view.trash_count === 0"
                @click="prepareClearTrash"
              >清空 Trash</button>
            </template>
          </div>

          <p v-if="entries.length === 0" class="library-empty">
            {{ search ? "当前范围没有符合搜索条件的 Paper。" : scope === "trash" ? "Trash 为空。" : "当前范围没有 Paper。" }}
          </p>

          <ol v-else class="library-list">
            <li
              v-for="entry in entries"
              :key="entry.path"
              :class="{ active: activePath === entry.path }"
              :draggable="!entry.trashed && !mutationBusy"
              @dragstart="onDragStart($event, entry.path)"
            >
              <label>
                <input
                  type="checkbox"
                  :checked="selectedPaths.includes(entry.path)"
                  :aria-label="`选择 ${entry.display_name || entry.code}`"
                  @change="toggleSelection(entry.path, $event.target.checked)"
                >
              </label>
              <button
                class="library-row"
                type="button"
                @click="activePath = entry.path"
              >
                <strong>{{ entry.display_name || entry.code }}</strong>
                <span>{{ entry.code }} · {{ entry.folder || (entry.trashed ? "Trash" : "未归类") }}</span>
                <p>{{ entry.summary }}</p>
              </button>
            </li>
          </ol>
        </section>

        <aside class="library-detail" aria-live="polite">
          <template v-if="activeEntry">
            <p class="library-eyebrow">Paper context</p>
            <h3>{{ activeEntry.display_name || activeEntry.code }}</h3>
            <code>{{ activeEntry.path }}</code>
            <p class="detail-summary">{{ activeEntry.summary }}</p>

            <dl>
              <div><dt>代号</dt><dd>{{ activeEntry.code }}</dd></div>
              <div><dt>文件夹</dt><dd>{{ activeEntry.folder || "未归类" }}</dd></div>
              <div><dt>Tags</dt><dd>{{ activeEntry.tags.length ? activeEntry.tags.join("、") : "未添加" }}</dd></div>
              <div><dt>Highlights</dt><dd>{{ activeEntry.highlight_names.length ? activeEntry.highlight_names.join("、") : "未命名" }}</dd></div>
              <div>
                <dt>创建</dt>
                <dd>{{ activeEntry.created.slice(0, 16).replace("T", " ") }}</dd>
              </div>
              <div>
                <dt>更新</dt>
                <dd>{{ activeEntry.updated.slice(0, 16).replace("T", " ") }}</dd>
              </div>
            </dl>

            <div class="detail-actions">
              <button
                type="button"
                :disabled="activeEntry.trashed || mutationBusy"
                @click="openPaper(activeEntry.path)"
              >编辑 Paper</button>
              <button
                type="button"
                :disabled="activeEntry.trashed || mutationBusy"
                @click="openFlashcard(activeEntry.path)"
              >打开 Flashcard</button>
              <button
                type="button"
                :disabled="activeEntry.trashed || mutationBusy"
                @click="runSystemAction('open', activeEntry.path)"
              >系统打开</button>
              <button
                type="button"
                :disabled="activeEntry.trashed || mutationBusy"
                @click="runSystemAction('reveal', activeEntry.path)"
              >在 Finder 中显示</button>
              <template v-if="!activeEntry.trashed">
                <button
                  type="button"
                  :aria-label="`移动 ${activeEntry.display_name || activeEntry.code}`"
                  :disabled="mutationBusy"
                  @click="openOperation('move', { paths: [activeEntry.path] })"
                >移动</button>
                <button type="button" :disabled="mutationBusy" @click="branchActive">
                  复制分支
                </button>
                <button
                  class="danger-action"
                  type="button"
                  :aria-label="`移至 Trash ${activeEntry.display_name || activeEntry.code}`"
                  :disabled="mutationBusy"
                  @click="openOperation('soft-delete', { paths: [activeEntry.path] })"
                >移至 Trash</button>
              </template>
              <template v-else>
                <button
                  type="button"
                  :aria-label="`恢复 ${activeEntry.display_name || activeEntry.code}`"
                  :disabled="mutationBusy"
                  @click="restorePaths([activeEntry.path])"
                >恢复</button>
                <button
                  class="danger-action"
                  type="button"
                  :aria-label="`永久删除 ${activeEntry.display_name || activeEntry.code}`"
                  :disabled="mutationBusy"
                  @click="openOperation('permanent-paper', { paths: [activeEntry.path] })"
                >永久删除</button>
              </template>
            </div>
          </template>
          <p v-else>选择一个 Paper 查看上下文。</p>
        </aside>
      </div>

      <section class="asset-health" aria-labelledby="asset-health-title">
        <h3 id="asset-health-title">资产健康 · {{ view.errors.length }}</h3>
        <p v-if="view.errors.length === 0">所有活动 Paper 都可读取。</p>
        <ul v-else>
          <li v-for="item in view.errors" :key="`${item.path}:${item.reason}`">
            <strong>损坏 Paper：{{ item.path }}</strong>
            <span>{{ item.reason }}</span>
          </li>
        </ul>
      </section>

      <section v-if="actionError && !operation" class="library-error" aria-live="assertive">
        <strong>{{ actionError.message }}</strong>
        <small>{{ actionError.layer }} · {{ actionError.code }}</small>
      </section>
      <p v-if="notice" class="library-notice" aria-live="polite">{{ notice }}</p>
      <p class="library-boundary-note">写入由 Python Core 执行；Vue 不直接操作 Markdown 或索引文件。</p>
    </main>

    <div
      v-if="operation"
      class="operation-backdrop"
      role="presentation"
      @click.self="closeOperation"
    >
      <section
        ref="operationDialog"
        class="operation-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="operation-title"
        tabindex="-1"
      >
        <h2 id="operation-title">
          {{
            operation.type === "move" ? "移动 Paper"
              : operation.type === "create-folder" ? "新建文件夹"
                : operation.type === "rename-folder" ? "重命名文件夹"
                  : operation.type === "merge-folder" ? "合并文件夹"
                    : operation.type === "soft-delete" ? "移至 Trash"
                      : operation.type === "soft-delete-folder" ? "文件夹移至 Trash"
                        : operation.type === "permanent-all" ? "清空 Trash"
                          : operation.type === "permanent-folder" ? "永久删除文件夹"
                            : "永久删除"
          }}
        </h2>

        <label v-if="operation.type === 'move'">
          <span>目标文件夹</span>
          <select v-model="operationDestination" :disabled="mutationBusy">
            <option value="">未归类</option>
            <option v-for="folder in view.folders" :key="folder" :value="folder">
              {{ folder }}
            </option>
          </select>
        </label>

        <label v-if="['create-folder', 'rename-folder'].includes(operation.type)">
          <span>文件夹名称</span>
          <input v-model="operationValue" type="text" :disabled="mutationBusy">
        </label>

        <label v-if="operation.type === 'merge-folder'">
          <span>合并目标</span>
          <select v-model="operationDestination" :disabled="mutationBusy">
            <option value="" disabled>选择目标文件夹</option>
            <option
              v-for="folder in view.folders.filter((item) => item !== operation.folder)"
              :key="folder"
              :value="folder"
            >{{ folder }}</option>
          </select>
        </label>

        <p v-if="operation.type === 'soft-delete'">
          {{ operation.paths.length }} 个 Paper 将移入 Trash，可稍后恢复。
        </p>
        <p v-else-if="operation.type === 'soft-delete-folder'">
          “{{ operation.folder }}”及其中 Paper 将移入 Trash，可逐项恢复。
        </p>
        <p v-else-if="operation.type.startsWith('permanent')" class="permanent-warning">
          将永久删除 {{ operationCount }} 个 Paper；此操作不可恢复。
        </p>

        <label v-if="operationNeedsExecute">
          <span>输入小写 execute</span>
          <input
            v-model="operationValue"
            type="text"
            :disabled="mutationBusy"
            autocomplete="off"
          >
        </label>

        <section v-if="actionError" class="library-error" aria-live="assertive">
          <strong>{{ actionError.message }}</strong>
          <small>{{ actionError.layer }} · {{ actionError.code }}</small>
        </section>

        <div class="operation-actions">
          <button type="button" :disabled="mutationBusy" @click="closeOperation">
            取消
          </button>
          <button
            :class="{ 'danger-action': ['soft-delete', 'soft-delete-folder'].includes(operation.type) || operation.type.startsWith('permanent') }"
            type="button"
            :disabled="
              mutationBusy ||
              (['create-folder', 'rename-folder'].includes(operation.type) && !operationValue.trim()) ||
              (operation.type === 'merge-folder' && !operationDestination)
            "
            @click="executeOperation"
          >{{ mutationBusy ? "正在执行…" : "确认执行" }}</button>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
.library-shell {
  display: grid;
  grid-template-columns: 72px 260px minmax(0, 1fr);
  min-height: 100vh;
  color: var(--ink);
  background: var(--canvas);
}

button,
input,
select {
  border-radius: var(--radius-xs, 2px);
}

button {
  border: 1px solid var(--ink);
  padding: 8px 12px;
  color: var(--ink);
  background: var(--paper);
  cursor: pointer;
}

button:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.library-eyebrow {
  margin: 0;
  color: var(--muted);
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.library-gate {
  display: grid;
  min-height: 100vh;
  padding: 32px;
  place-items: center;
  background: var(--canvas);
}

.library-gate > section {
  width: min(680px, 100%);
  padding: 40px;
  border: 1px solid var(--rule);
  border-top: 4px solid var(--accent);
  background: var(--paper);
}

.library-gate h1 {
  margin: 10px 0 16px;
  font-family: var(--font-display);
  font-size: clamp(2rem, 6vw, 3.5rem);
  font-weight: 500;
  line-height: 1.08;
}

.library-gate button {
  margin-top: 20px;
  color: var(--paper);
  background: var(--accent);
}

.library-gate-error {
  border-top-color: var(--danger) !important;
}

.library-rail {
  position: fixed;
  z-index: 1;
  inset: 0 auto 0 0;
  display: flex;
  width: 72px;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  overflow-y: auto;
  padding: 18px 8px;
  color: var(--paper);
  background: var(--rail);
}

.library-brand {
  display: grid;
  width: 38px;
  height: 38px;
  border: 1px solid var(--paper);
  place-items: center;
  font-family: var(--font-display);
  font-size: 1.4rem;
}

.library-destination {
  display: grid;
  width: 52px;
  min-height: 50px;
  border: 0;
  padding: 0;
  place-items: center;
  color: var(--rail-muted);
  background: transparent;
  font-weight: 700;
}

.library-destination small {
  font-size: 0.58rem;
  font-weight: 500;
}

.library-destination.is-active {
  border-left: 3px solid var(--signal);
  color: var(--paper);
  background: var(--rail-active);
}

.library-local {
  margin-top: auto;
  font: 0.58rem var(--font-mono);
  letter-spacing: 0.12em;
}

.library-context {
  grid-column: 2;
  min-width: 0;
  padding: 28px 18px;
  border-right: 1px solid var(--rule);
  background: var(--soft);
}

.library-context h1,
.library-workspace h2 {
  margin: 8px 0;
  font-family: var(--font-display);
  font-weight: 500;
}

.library-context header > p:last-child {
  color: var(--muted);
  font-size: 0.78rem;
}

.library-scopes {
  display: grid;
  gap: 6px;
  margin-top: 28px;
}

.library-scopes h2,
.trash-folders h2 {
  margin: 0 0 6px;
  font-size: 0.72rem;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

.library-scopes button {
  display: flex;
  min-width: 0;
  justify-content: space-between;
  border-color: transparent;
  overflow-wrap: anywhere;
  text-align: left;
  background: transparent;
}

.library-scopes button.selected {
  border-color: var(--rule);
  border-left: 3px solid var(--signal);
  background: var(--paper);
}

.scope-label {
  margin: 14px 0 0;
  color: var(--muted);
  font-size: 0.72rem;
  font-weight: 700;
}

.trash-folders {
  margin-top: 24px;
  padding-top: 18px;
  border-top: 1px solid var(--rule);
}

.trash-folders ul {
  display: grid;
  gap: 8px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.trash-folders li {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto auto;
  align-items: center;
  gap: 5px;
}

.trash-folders li > span {
  min-width: 0;
  overflow-wrap: anywhere;
}

.trash-folders button,
.folder-tools button {
  padding: 5px 7px;
  font-size: 0.7rem;
}

.folder-tools {
  display: grid;
  gap: 6px;
  margin-top: 24px;
  padding-top: 18px;
  border-top: 1px solid var(--rule);
}

.folder-tools h2 {
  margin: 0 0 4px;
  font-size: 0.72rem;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

.reveal-vault {
  width: 100%;
}

.vault-tools {
  display: grid;
  gap: 7px;
  margin-top: 28px;
}

.library-workspace {
  grid-column: 3;
  min-width: 0;
  padding: 30px clamp(22px, 4vw, 52px) 64px;
}

.library-workspace-header {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 20px;
  padding-bottom: 18px;
  border-bottom: 1px solid var(--rule);
}

.library-workspace-header > div {
  min-width: 0;
}

.library-workspace-header h2 {
  font-size: clamp(2rem, 4vw, 3.2rem);
  overflow-wrap: anywhere;
}

.library-workspace-header > span {
  color: var(--accent);
  font: 0.78rem var(--font-mono);
}

.library-toolbar {
  display: grid;
  grid-template-columns: minmax(220px, 1fr) minmax(160px, 220px) repeat(3, auto);
  align-items: end;
  gap: 12px;
  margin: 24px 0;
}

.library-toolbar label {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 7px;
  font-size: 0.82rem;
  font-weight: 650;
}

.library-toolbar input,
.library-toolbar select {
  grid-column: 1 / -1;
  min-width: 0;
  width: 100%;
  border: 1px solid var(--rule);
  padding: 10px 11px;
  color: var(--ink);
  background: var(--field);
}

.library-toolbar small {
  color: var(--muted);
  font-family: var(--font-mono);
}

.library-stage {
  display: grid;
  grid-template-columns: minmax(280px, 1fr) minmax(240px, 0.72fr);
  gap: 24px;
}

.library-results,
.library-detail,
.asset-health {
  border: 1px solid var(--rule);
  background: var(--paper);
}

.library-results {
  border-top: 3px solid var(--signal);
}

.library-results > header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 16px;
  border-bottom: 1px solid var(--rule);
}

.mutation-toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
  padding: 10px 16px;
  border-bottom: 1px solid var(--rule);
  background: var(--soft);
}

.mutation-toolbar button {
  padding: 6px 9px;
  border-color: var(--rule);
  font-size: 0.74rem;
}

.danger-action {
  border-color: var(--danger) !important;
  color: var(--danger);
}

.library-results h3,
.library-detail h3,
.asset-health h3 {
  margin: 0;
  font-family: var(--font-display);
  font-size: 1.25rem;
  font-weight: 500;
}

.library-results header div {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.library-results header button {
  padding: 5px 8px;
  border-color: var(--rule);
  font-size: 0.72rem;
}

.library-list {
  margin: 0;
  padding: 0;
  list-style: none;
}

.library-list li {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  align-items: start;
  gap: 8px;
  padding: 12px 14px;
  border-bottom: 1px solid var(--rule);
}

.library-list li[draggable="true"] {
  cursor: grab;
}

.library-list li[draggable="true"]:active {
  cursor: grabbing;
}

.library-list li.active {
  border-left: 3px solid var(--signal);
  background: var(--soft);
}

.library-list label {
  padding-top: 9px;
}

.library-list input[type="checkbox"] {
  accent-color: var(--accent);
}

.library-row {
  display: grid;
  gap: 4px;
  min-width: 0;
  border: 0;
  padding: 6px;
  text-align: left;
  background: transparent;
}

.library-row span,
.library-row p {
  margin: 0;
  overflow-wrap: anywhere;
  color: var(--muted);
}

.library-row span {
  font: 0.7rem var(--font-mono);
}

.library-row p {
  display: -webkit-box;
  overflow: hidden;
  font-size: 0.82rem;
  line-height: 1.4;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.library-empty {
  padding: 24px;
  color: var(--muted);
}

.library-detail {
  align-self: start;
  padding: 24px;
  border-top: 3px solid var(--accent);
}

.library-detail code {
  display: block;
  margin-top: 10px;
  overflow-wrap: anywhere;
  color: var(--muted);
  font-size: 0.72rem;
}

.detail-summary {
  margin: 24px 0;
  font-family: var(--font-display);
  font-size: 1.25rem;
  line-height: 1.5;
  white-space: pre-wrap;
}

.library-detail dl {
  display: grid;
  gap: 9px;
}

.library-detail dl div {
  display: grid;
  grid-template-columns: 84px minmax(0, 1fr);
  gap: 8px;
}

.library-detail dt {
  color: var(--muted);
}

.library-detail dd {
  margin: 0;
  overflow-wrap: anywhere;
}

.detail-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
  margin-top: 24px;
}

.detail-actions button {
  border-color: var(--rule);
}

.trash-note,
.library-boundary-note {
  color: var(--muted);
  font-size: 0.78rem;
}

.asset-health {
  margin-top: 24px;
  padding: 20px;
}

.asset-health p {
  margin-bottom: 0;
  color: var(--muted);
}

.asset-health ul {
  display: grid;
  gap: 10px;
  margin-bottom: 0;
  padding-left: 20px;
}

.asset-health li {
  color: var(--danger);
}

.asset-health li span {
  display: block;
  margin-top: 3px;
  color: var(--muted);
}

.asset-health li strong,
.asset-health li span {
  overflow-wrap: anywhere;
}

.library-error {
  display: grid;
  gap: 6px;
  margin: 16px 0;
  padding: 14px;
  border: 1px solid var(--danger);
  background: var(--danger-soft);
}

.library-error small {
  color: var(--muted);
  font-family: var(--font-mono);
}

.library-notice {
  color: var(--success);
  font-weight: 650;
}

.operation-backdrop {
  position: fixed;
  z-index: 10;
  inset: 0;
  display: grid;
  padding: 20px;
  place-items: center;
  background: rgb(30 37 35 / 58%);
}

.operation-dialog {
  width: min(520px, 100%);
  max-height: calc(100vh - 40px);
  overflow: auto;
  border: 1px solid var(--ink);
  border-top: 4px solid var(--signal);
  padding: 26px;
  background: var(--paper);
}

.operation-dialog h2 {
  margin: 0 0 18px;
  font-family: var(--font-display);
  font-size: 1.8rem;
  font-weight: 500;
}

.operation-dialog label {
  display: grid;
  gap: 7px;
  margin: 16px 0;
  font-weight: 650;
}

.operation-dialog input,
.operation-dialog select {
  min-width: 0;
  width: 100%;
  border: 1px solid var(--rule);
  padding: 10px;
  color: var(--ink);
  background: var(--field);
}

.permanent-warning {
  border: 1px solid var(--danger);
  padding: 12px;
  color: var(--danger);
  background: var(--danger-soft);
}

.operation-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 22px;
}

.operation-dialog .danger-action {
  color: var(--paper);
  background: var(--danger);
}

@media (max-width: 1080px) {
  .library-stage {
    grid-template-columns: 1fr;
  }

  .library-toolbar {
    grid-template-columns: minmax(220px, 1fr) minmax(140px, 0.5fr);
  }
}

@media (max-width: 820px) {
  .library-shell {
    grid-template-columns: 56px minmax(0, 1fr);
  }

  .library-rail {
    grid-row: 1 / span 2;
    width: 56px;
  }

  .library-context {
    border-right: 0;
    border-bottom: 1px solid var(--rule);
  }

  .library-workspace {
    grid-column: 2;
    padding: 24px 18px 48px;
  }

  .library-toolbar {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 520px) {
  .library-shell {
    display: block;
  }

  .library-rail {
    position: static;
    width: auto;
    height: auto;
    flex-direction: row;
    justify-content: space-between;
    overflow-y: visible;
  }

  .library-local {
    margin: 0;
  }

  .library-context {
    padding: 22px 16px;
  }

  .library-workspace {
    padding: 24px 16px 44px;
  }

  .library-workspace-header {
    align-items: start;
    flex-direction: column;
  }

  .library-results > header {
    align-items: start;
    flex-direction: column;
  }

  .library-detail {
    padding: 20px 16px;
  }

  .library-gate {
    padding: 16px;
  }

  .library-gate > section {
    padding: 24px;
  }
}
</style>

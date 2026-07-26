<script setup>
import { computed, onMounted, onUnmounted, ref } from "vue";

import { bridgeRequest, openSystemTarget } from "./bridge.js";

defineProps({
  runtime: {
    type: Object,
    required: true,
  },
});

const emit = defineEmits(["runtime-blocked", "open-paper", "open-flashcard"]);

const searchInput = ref(null);
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
let queryGeneration = 0;

const entries = computed(() => view.value?.entries ?? []);
const activeEntry = computed(
  () => entries.value.find((entry) => entry.path === activePath.value) ?? null,
);
const selectedCount = computed(() => selectedPaths.value.length);

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
    return;
  }
  target.value = visible;
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

async function refresh({ clear = false } = {}) {
  if (clear) {
    clearSelection();
    activePath.value = null;
  }
  const generation = ++queryGeneration;
  busy.value = true;
  queryError.value = null;
  notice.value = "";
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
  emit("open-paper", path);
}

function openFlashcard(path = activeReadablePath()) {
  emit("open-flashcard", path);
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
  if (event.metaKey && event.key.toLocaleLowerCase() === "f") {
    event.preventDefault();
    searchInput.value?.focus();
  } else if (event.key === "Escape" && selectedPaths.value.length > 0) {
    clearSelection();
  }
}

onMounted(() => {
  window.addEventListener("keydown", onWindowKeydown);
  refresh();
});

onUnmounted(() => {
  queryGeneration += 1;
  window.removeEventListener("keydown", onWindowKeydown);
});
</script>

<template>
  <main v-if="busy && !view" class="library-gate" aria-live="polite">
    <section>
      <p class="library-eyebrow">Road v0.4 · CP8</p>
      <h1>正在读取 Library</h1>
      <p>搜索、排序与 scope 由 Python application service 执行。</p>
    </section>
  </main>

  <main v-else-if="!view" class="library-gate" aria-live="assertive">
    <section class="library-gate-error">
      <p class="library-eyebrow">Library read slice 已阻塞</p>
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
        <p class="library-eyebrow">Road v0.4 · CP8</p>
        <h1 id="library-scopes-title">Library</h1>
        <p>只读索引 · {{ runtime.core_version }}</p>
      </header>

      <nav class="library-scopes" aria-label="Library scopes">
        <h2>Scopes</h2>
        <button
          type="button"
          :class="{ selected: scope === 'all' }"
          @click="setScope('all')"
        >全部 Paper</button>
        <button
          type="button"
          :class="{ selected: scope === 'unfiled' }"
          @click="setScope('unfiled')"
        >未归类</button>
        <p v-if="view.folders.length" class="scope-label">文件夹</p>
        <button
          v-for="folder in view.folders"
          :key="folder"
          type="button"
          :class="{ selected: scope === `folder:${folder}` }"
          @click="setScope(`folder:${folder}`)"
        >{{ folder }}</button>
        <button
          type="button"
          :class="{ selected: scope === 'trash' }"
          @click="setScope('trash')"
        >Trash <span>{{ view.trash_count }}</span></button>
      </nav>

      <section v-if="scope === 'trash' && view.trash_folders.length" class="trash-folders">
        <h2>Trash 文件夹</h2>
        <ul>
          <li v-for="folder in view.trash_folders" :key="folder">{{ folder }}</li>
        </ul>
      </section>

      <button
        class="reveal-vault"
        type="button"
        @click="runSystemAction('reveal', '.')"
      >在 Finder 中显示 Vault</button>
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
            placeholder="名称、代号、Summary、Tags 或 Highlight 名称"
            @input="updateQuery"
          >
          <small>⌘F</small>
        </label>
        <label>
          <span>排序</span>
          <select v-model="sort" @change="updateQuery">
            <option value="updated_desc">最近更新</option>
            <option value="created_desc">最近创建</option>
            <option value="created_asc">最早创建</option>
            <option value="name">名称</option>
          </select>
        </label>
        <button type="button" :disabled="busy" @click="refresh({ clear: true })">
          {{ busy ? "读取中…" : "刷新" }}
        </button>
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

          <p v-if="entries.length === 0" class="library-empty">
            {{ search ? "当前范围没有符合搜索条件的 Paper。" : scope === "trash" ? "Trash 为空。" : "当前范围没有 Paper。" }}
          </p>

          <ol v-else class="library-list">
            <li
              v-for="entry in entries"
              :key="entry.path"
              :class="{ active: activePath === entry.path }"
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
              <div><dt>创建</dt><dd>{{ activeEntry.created }}</dd></div>
              <div><dt>更新</dt><dd>{{ activeEntry.updated }}</dd></div>
            </dl>

            <div class="detail-actions">
              <button
                type="button"
                :disabled="activeEntry.trashed"
                @click="openPaper(activeEntry.path)"
              >编辑 Paper</button>
              <button
                type="button"
                :disabled="activeEntry.trashed"
                @click="openFlashcard(activeEntry.path)"
              >打开 Flashcard</button>
              <button
                type="button"
                :disabled="activeEntry.trashed"
                @click="runSystemAction('open', activeEntry.path)"
              >系统打开</button>
              <button
                type="button"
                :disabled="activeEntry.trashed"
                @click="runSystemAction('reveal', activeEntry.path)"
              >在 Finder 中显示</button>
            </div>
            <p v-if="activeEntry.trashed" class="trash-note">
              Trash 内容在 CP8 只读；恢复与永久删除属于 CP9。
            </p>
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

      <section v-if="actionError" class="library-error" aria-live="assertive">
        <strong>{{ actionError.message }}</strong>
        <small>{{ actionError.layer }} · {{ actionError.code }}</small>
      </section>
      <p v-if="notice" class="library-notice" aria-live="polite">{{ notice }}</p>
      <p class="cp9-note">移动、分支、文件夹管理、Trash 恢复与永久删除在 CP9 接入。</p>
    </main>
  </div>
</template>

<style scoped>
.library-shell {
  --canvas: #eceae4;
  --paper: #fffefa;
  --ink: #1e2523;
  --muted: #646b68;
  --accent: #2e5d57;
  --signal: #9a4e3f;
  --rule: #c8c9c2;
  --danger: #a33e3e;
  display: grid;
  grid-template-columns: 72px 230px minmax(0, 1fr);
  min-height: 100vh;
  color: var(--ink);
  background: var(--canvas);
}

button,
input,
select {
  border-radius: 0;
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
  color: var(--muted, #646b68);
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
  background: #eceae4;
}

.library-gate > section {
  width: min(680px, 100%);
  padding: 40px;
  border: 1px solid #c8c9c2;
  background: #fffefa;
}

.library-gate h1 {
  margin: 10px 0 16px;
  font-family: Georgia, "Times New Roman", serif;
  font-size: clamp(2rem, 6vw, 3.5rem);
  font-weight: 500;
  line-height: 1.08;
}

.library-gate button {
  margin-top: 20px;
  color: #fffefa;
  background: #2e5d57;
}

.library-gate-error {
  border-top: 4px solid #a33e3e !important;
}

.library-rail {
  position: sticky;
  top: 0;
  display: flex;
  min-height: 100vh;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  padding: 18px 8px;
  color: var(--paper);
  background: var(--ink);
}

.library-brand {
  display: grid;
  width: 38px;
  height: 38px;
  border: 1px solid var(--paper);
  place-items: center;
  font-family: Georgia, "Times New Roman", serif;
  font-size: 1.4rem;
}

.library-destination {
  display: grid;
  width: 52px;
  min-height: 50px;
  border: 0;
  padding: 0;
  place-items: center;
  color: #b9c0bd;
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
  background: #2d3532;
}

.library-local {
  margin-top: auto;
  font: 0.58rem ui-monospace, SFMono-Regular, Menlo, monospace;
  letter-spacing: 0.12em;
}

.library-context {
  min-width: 0;
  padding: 28px 18px;
  border-right: 1px solid var(--rule);
  background: #f4f3ee;
}

.library-context h1,
.library-workspace h2 {
  margin: 8px 0;
  font-family: Georgia, "Times New Roman", serif;
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
  justify-content: space-between;
  border-color: transparent;
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
  margin: 0;
  padding-left: 20px;
}

.reveal-vault {
  width: 100%;
  margin-top: 28px;
}

.library-workspace {
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

.library-workspace-header h2 {
  font-size: clamp(2rem, 4vw, 3.2rem);
}

.library-workspace-header > span {
  color: var(--accent);
  font: 0.78rem ui-monospace, SFMono-Regular, Menlo, monospace;
}

.library-toolbar {
  display: grid;
  grid-template-columns: minmax(220px, 1fr) minmax(160px, 220px) auto;
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
  background: #fff;
}

.library-toolbar small {
  color: var(--muted);
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
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

.library-results h3,
.library-detail h3,
.asset-health h3 {
  margin: 0;
  font-family: Georgia, "Times New Roman", serif;
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

.library-list li.active {
  border-left: 3px solid var(--signal);
  background: #f4f3ee;
}

.library-list label {
  padding-top: 9px;
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
  font: 0.7rem ui-monospace, SFMono-Regular, Menlo, monospace;
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
  font-family: Georgia, "Times New Roman", serif;
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
.cp9-note {
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

.library-error {
  display: grid;
  gap: 6px;
  margin: 16px 0;
  padding: 14px;
  border: 1px solid var(--danger);
  background: #fff7f4;
}

.library-error small {
  color: var(--muted);
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
}

.library-notice {
  color: #2f6b50;
  font-weight: 650;
}

@media (max-width: 1080px) {
  .library-stage {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 820px) {
  .library-shell {
    grid-template-columns: 56px minmax(0, 1fr);
  }

  .library-rail {
    grid-row: 1 / span 2;
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
    min-height: auto;
    flex-direction: row;
    justify-content: space-between;
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

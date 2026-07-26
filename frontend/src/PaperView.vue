<script setup>
import { computed, onMounted, onUnmounted, ref } from "vue";

import { bridgeRequest } from "./bridge.js";

const props = defineProps({
  runtime: {
    type: Object,
    required: true,
  },
  initialPath: {
    type: String,
    default: null,
  },
});

const emit = defineEmits(["runtime-blocked", "open-flashcard"]);

let highlightKey = 0;
let dailyTimer;
const screen = ref("loading");
const startup = ref(null);
const entries = ref([]);
const paper = ref(null);
const form = ref(blankForm());
const savedForm = ref("");
const busyAction = ref("");
const notice = ref("");
const actionError = ref(null);
const startupError = ref(null);
const deletePending = ref(false);
const enteringWorkspace = ref(false);

const isBusy = computed(() => busyAction.value !== "");
const isDirty = computed(
  () => paper.value !== null && serializeForm(form.value) !== savedForm.value,
);

function blankForm() {
  return {
    displayName: "",
    summary: "",
    tags: "",
    highlights: [],
  };
}

function editableHighlight(value = {}) {
  highlightKey += 1;
  return {
    key: highlightKey,
    displayName: value.display_name ?? "",
    content: value.content ?? "",
  };
}

function serializeForm(value) {
  return JSON.stringify({
    displayName: value.displayName,
    summary: value.summary,
    tags: value.tags,
    highlights: value.highlights.map(({ displayName, content }) => ({
      displayName,
      content,
    })),
  });
}

function applyPaper(nextPaper) {
  const nextForm = {
    displayName: nextPaper.display_name ?? "",
    summary: nextPaper.summary ?? "",
    tags: Array.isArray(nextPaper.tags) ? nextPaper.tags.join(", ") : "",
    highlights: (nextPaper.highlights ?? []).map(editableHighlight),
  };
  paper.value = nextPaper;
  form.value = nextForm;
  savedForm.value = serializeForm(nextForm);
  actionError.value = null;
  deletePending.value = false;
}

function normalizeError(error) {
  if (error && typeof error === "object") {
    return {
      code: error.code ?? "operation_failed",
      layer: error.layer ?? "vue_ui",
      message: error.message ?? "本地操作未完成。",
      recovery: error.recovery ?? "review",
    };
  }
  return {
    code: "operation_failed",
    layer: "vue_ui",
    message: "本地操作未完成。",
    recovery: "review",
  };
}

function paperError(error, fallback) {
  if (error.code === "stale_snapshot") {
    return "Paper 已在外部修改；未覆盖。请重新打开后决定如何处理。";
  }
  if (error.code === "not_found") {
    return "Paper 已在外部删除或移动；未保存。请刷新 Paper 列表。";
  }
  if (error.code === "commit_unknown") {
    return "写入请求已发出，但结果未知。已停止后续写入；重启 Core 后请先重新读取磁盘状态。";
  }
  return `${fallback}：${error.message}`;
}

function handleError(rawError, fallback, target = actionError) {
  const error = normalizeError(rawError);
  const visible = { ...error, message: paperError(error, fallback) };
  if (
    error.layer === "tauri_host" ||
    ["commit_unknown", "protocol_mismatch", "sidecar_unavailable"].includes(error.code)
  ) {
    emit("runtime-blocked", visible);
    return;
  }
  target.value = visible;
}

async function loadEntries() {
  const result = await bridgeRequest("library.query", {
    scope: "all",
    search: "",
    sort: "updated_desc",
  });
  entries.value = result.entries ?? [];
}

async function enterWorkspace() {
  if (enteringWorkspace.value) {
    return;
  }
  enteringWorkspace.value = true;
  window.clearTimeout(dailyTimer);
  screen.value = "loading";
  try {
    await loadEntries();
    const nextPaper = props.initialPath
      ? await bridgeRequest("paper.open", { path: props.initialPath })
      : await bridgeRequest("paper.create_draft", {});
    applyPaper(nextPaper);
    screen.value = "editor";
  } catch (error) {
    screen.value = "error";
    handleError(error, "无法打开 Paper 工作台", startupError);
  } finally {
    enteringWorkspace.value = false;
  }
}

async function loadStartup() {
  try {
    startup.value = await bridgeRequest("startup.load", {});
    if (startup.value.state !== "ready") {
      screen.value = "startup_gate";
      return;
    }
    if (startup.value.show_daily_card) {
      screen.value = "daily";
      dailyTimer = window.setTimeout(enterWorkspace, 3000);
      return;
    }
    await enterWorkspace();
  } catch (error) {
    screen.value = "error";
    handleError(error, "无法读取启动状态", startupError);
  }
}

function confirmDiscard() {
  return (
    !isDirty.value ||
    window.confirm("当前未保存的更改将丢失。是否继续？")
  );
}

function openFlashcard() {
  if (isBusy.value || !confirmDiscard()) {
    return;
  }
  emit("open-flashcard", paper.value?.path ?? null);
}

async function createDraft() {
  if (isBusy.value || !confirmDiscard()) {
    return;
  }
  busyAction.value = "draft";
  notice.value = "";
  try {
    const draft = await bridgeRequest("paper.create_draft", {});
    applyPaper(draft);
  } catch (error) {
    handleError(error, "无法新建 Paper");
  } finally {
    busyAction.value = "";
  }
}

async function openPaper(path, { discard = false } = {}) {
  if (isBusy.value || (!discard && !confirmDiscard())) {
    return;
  }
  busyAction.value = "open";
  notice.value = "";
  try {
    applyPaper(await bridgeRequest("paper.open", { path }));
  } catch (error) {
    handleError(error, "无法打开 Paper");
  } finally {
    busyAction.value = "";
  }
}

function addHighlight() {
  form.value.highlights.push(editableHighlight());
}

function moveHighlight(index, offset) {
  const destination = index + offset;
  if (destination < 0 || destination >= form.value.highlights.length) {
    return;
  }
  const [item] = form.value.highlights.splice(index, 1);
  form.value.highlights.splice(destination, 0, item);
}

function removeHighlight(index) {
  form.value.highlights.splice(index, 1);
}

async function refreshEntriesAfterMutation() {
  try {
    await loadEntries();
  } catch (error) {
    handleError(error, "写入已完成，但无法刷新 Paper 列表");
  }
}

async function savePaper() {
  if (isBusy.value || paper.value === null) {
    return;
  }
  actionError.value = null;
  notice.value = "";
  if (!form.value.summary.trim()) {
    actionError.value = {
      code: "validation_failed",
      layer: "vue_ui",
      message: "Summary 不能为空。",
      recovery: "correct_input",
    };
    return;
  }
  busyAction.value = "save";
  try {
    const stored = await bridgeRequest("paper.save", {
      edit_token: paper.value.edit_token,
      summary: form.value.summary,
      display_name: form.value.displayName,
      highlights: form.value.highlights.map((highlight) => ({
        display_name: highlight.displayName,
        content: highlight.content,
      })),
      tags: form.value.tags.split(","),
    });
    applyPaper(stored);
    notice.value = "Paper 已保存。";
    await refreshEntriesAfterMutation();
  } catch (error) {
    handleError(error, "无法保存 Paper");
  } finally {
    busyAction.value = "";
  }
}

async function reopenCurrent() {
  if (paper.value?.path) {
    await openPaper(paper.value.path, { discard: true });
  }
}

async function recoverMissingPaper() {
  busyAction.value = "recover";
  actionError.value = null;
  try {
    await loadEntries();
    applyPaper(await bridgeRequest("paper.create_draft", {}));
    notice.value = "已刷新磁盘状态；当前为新的空白 Paper。";
  } catch (error) {
    handleError(error, "无法刷新磁盘状态");
  } finally {
    busyAction.value = "";
  }
}

async function confirmDelete() {
  if (isBusy.value || paper.value?.path == null) {
    return;
  }
  busyAction.value = "delete";
  actionError.value = null;
  notice.value = "";
  try {
    const result = await bridgeRequest("paper.soft_delete", {
      edit_token: paper.value.edit_token,
    });
    if (result.error) {
      throw {
        code: "operation_failed",
        layer: "application_service",
        message: result.error,
        recovery: "refresh",
      };
    }
    notice.value = "Paper 已移入回收站。";
  } catch (error) {
    handleError(error, "无法删除 Paper");
    busyAction.value = "";
    return;
  }
  try {
    await loadEntries();
    applyPaper(await bridgeRequest("paper.create_draft", {}));
    notice.value = "Paper 已移入回收站。";
  } catch (error) {
    handleError(error, "Paper 已删除，但无法刷新工作台");
  } finally {
    busyAction.value = "";
  }
}

function onWindowKeydown(event) {
  if (screen.value === "daily" && ["Enter", "Return"].includes(event.key)) {
    event.preventDefault();
    enterWorkspace();
    return;
  }
  if (
    screen.value === "editor" &&
    event.metaKey &&
    event.key.toLocaleLowerCase() === "s"
  ) {
    event.preventDefault();
    savePaper();
  }
}

onMounted(() => {
  window.addEventListener("keydown", onWindowKeydown);
  loadStartup();
});

onUnmounted(() => {
  window.clearTimeout(dailyTimer);
  window.removeEventListener("keydown", onWindowKeydown);
});
</script>

<template>
  <main v-if="screen === 'loading'" class="paper-gate" aria-live="polite">
    <section>
      <p class="paper-eyebrow">Road v0.4 · CP6</p>
      <h1>正在读取本地 Paper</h1>
      <p>Vue 正通过受限本地边界读取启动状态。</p>
    </section>
  </main>

  <main v-else-if="screen === 'daily'" class="paper-gate daily-gate">
    <section>
      <p class="paper-eyebrow">每日一张</p>
      <blockquote>
        写作像走迷宫。撞墙时，退回走错的路口，换一条路。
      </blockquote>
      <p>玛格丽特·阿特伍德（意译）</p>
      <button type="button" @click="enterWorkspace">开始写</button>
      <small>按 Enter，或等待三秒。</small>
    </section>
  </main>

  <main v-else-if="screen === 'startup_gate'" class="paper-gate">
    <section>
      <p class="paper-eyebrow">启动 gate · {{ startup?.state }}</p>
      <h1>当前还不能进入 Paper</h1>
      <p>{{ startup?.message || "需要先完成 Vault 或迁移流程。" }}</p>
      <p>CP9 将接入目录选择、Vault 确认与迁移；此阶段不会绕过安全 gate。</p>
    </section>
  </main>

  <main v-else-if="screen === 'error'" class="paper-gate" aria-live="assertive">
    <section class="paper-gate-error">
      <p class="paper-eyebrow">Paper slice 已阻塞</p>
      <h1>无法安全读取工作区</h1>
      <p>{{ startupError?.message ?? "本地启动流程未完成。" }}</p>
      <dl v-if="startupError">
        <div><dt>错误码</dt><dd>{{ startupError.code }}</dd></div>
        <div><dt>层级</dt><dd>{{ startupError.layer }}</dd></div>
        <div><dt>恢复</dt><dd>{{ startupError.recovery }}</dd></div>
      </dl>
    </section>
  </main>

  <div v-else class="paper-shell">
    <nav class="paper-rail" aria-label="全局工作区">
      <span class="paper-brand" aria-label="keikeu">K</span>
      <span class="paper-destination is-active" aria-current="page">P<small>Paper</small></span>
      <button
        class="paper-destination"
        type="button"
        aria-label="打开 Flashcard"
        :disabled="isBusy"
        @click="openFlashcard"
      >F<small>Flash</small></button>
      <span class="paper-destination" aria-disabled="true">L<small>CP8</small></span>
      <span class="paper-local">LOCAL</span>
    </nav>

    <aside class="paper-context" aria-labelledby="paper-list-title">
      <header>
        <p class="paper-eyebrow">Road v0.4 · CP6</p>
        <h1 id="paper-list-title">Paper 工作台</h1>
        <p>Python Core 已连接 · {{ runtime.core_version }}</p>
      </header>
      <button class="new-paper" type="button" :disabled="isBusy" @click="createDraft">
        + 新建 Paper
      </button>
      <section>
        <h2>最近的 Paper <span>{{ entries.length }}</span></h2>
        <p v-if="entries.length === 0" class="empty-list">Vault 中还没有已保存 Paper。</p>
        <ul v-else class="paper-picker">
          <li v-for="entry in entries" :key="entry.path">
            <button
              type="button"
              :class="{ selected: entry.path === paper?.path }"
              :disabled="isBusy"
              @click="openPaper(entry.path)"
            >
              <strong>{{ entry.display_name || entry.code }}</strong>
              <span>{{ entry.code }}</span>
              <small>{{ entry.path }}</small>
            </button>
          </li>
        </ul>
      </section>
    </aside>

    <main class="paper-workspace">
      <header class="paper-workspace-header">
        <div>
          <p class="paper-eyebrow">{{ paper?.path ? "编辑 Paper" : "新 Paper" }}</p>
          <h2>{{ form.displayName || paper?.code }}</h2>
        </div>
        <span :class="{ dirty: isDirty }">{{ isDirty ? "尚未保存" : "磁盘状态已同步" }}</span>
      </header>

      <div class="paper-stage">
        <form class="paper-editor" @submit.prevent="savePaper">
          <label>
            <span>系统编号</span>
            <input :value="paper?.code" name="code" readonly>
          </label>
          <label>
            <span>Paper 名称（可选）</span>
            <input v-model="form.displayName" name="display_name" maxlength="120">
          </label>
          <label>
            <span>Summary <b aria-hidden="true">*</b></span>
            <textarea v-model="form.summary" name="summary" rows="5" required />
          </label>

          <section class="initial-copy" aria-labelledby="initial-copy-title">
            <h3 id="initial-copy-title">初稿副本（只读）</h3>
            <p>{{ paper?.initial_summary || "初稿副本会在首次保存后冻结，只读保留。" }}</p>
          </section>

          <fieldset class="paper-highlights">
            <legend>Highlights（可选）</legend>
            <p>顺序会成为 Flashcard 顺序；按钮路径可由键盘完成。</p>
            <ol>
              <li v-for="(highlight, index) in form.highlights" :key="highlight.key">
                <span class="highlight-number">{{ String(index + 1).padStart(2, "0") }}</span>
                <div class="highlight-fields">
                  <label>
                    <span>Highlight {{ index + 1 }} 命名（可选）</span>
                    <input v-model="highlight.displayName">
                  </label>
                  <label>
                    <span>Highlight {{ index + 1 }} 内容</span>
                    <textarea v-model="highlight.content" rows="3" />
                  </label>
                </div>
                <div class="highlight-actions" :aria-label="`Highlight ${index + 1} 排序`">
                  <button
                    type="button"
                    :disabled="index === 0 || isBusy"
                    @click="moveHighlight(index, -1)"
                  >上移</button>
                  <button
                    type="button"
                    :disabled="index === form.highlights.length - 1 || isBusy"
                    @click="moveHighlight(index, 1)"
                  >下移</button>
                  <button type="button" :disabled="isBusy" @click="removeHighlight(index)">
                    删除
                  </button>
                </div>
              </li>
            </ol>
            <button type="button" :disabled="isBusy" @click="addHighlight">+ 添加 Highlight</button>
          </fieldset>

          <label>
            <span>Tags（用逗号分隔）</span>
            <input v-model="form.tags" name="tags">
          </label>

          <section v-if="actionError" class="paper-error" aria-live="assertive">
            <strong>{{ actionError.message }}</strong>
            <small>{{ actionError.layer }} · {{ actionError.code }}</small>
            <button
              v-if="actionError.code === 'stale_snapshot' && paper?.path"
              type="button"
              :disabled="isBusy"
              @click="reopenCurrent"
            >丢弃本地更改并重新打开</button>
            <button
              v-else-if="actionError.code === 'not_found'"
              type="button"
              :disabled="isBusy"
              @click="recoverMissingPaper"
            >刷新列表并新建 Paper</button>
          </section>
          <p v-if="notice" class="paper-notice" aria-live="polite">{{ notice }}</p>

          <div class="paper-actions">
            <button class="primary-action" type="submit" :disabled="isBusy">
              {{ busyAction === "save" ? "正在保存…" : "保存 · ⌘S" }}
            </button>
            <button
              type="button"
              :disabled="isBusy || paper?.path == null"
              @click="deletePending = true"
            >移入回收站</button>
          </div>

          <section
            v-if="deletePending"
            class="delete-confirm"
            role="group"
            aria-labelledby="delete-confirm-title"
          >
            <h3 id="delete-confirm-title">确认软删除这个 Paper？</h3>
            <p>
              它会移动到 Vault 的回收站；CP9 再接入恢复流程。
              <strong v-if="isDirty">当前未保存修改不会写入磁盘。</strong>
            </p>
            <div>
              <button type="button" :disabled="isBusy" @click="deletePending = false">
                取消
              </button>
              <button class="danger-action" type="button" :disabled="isBusy" @click="confirmDelete">
                {{ busyAction === "delete" ? "正在移动…" : "确认移入回收站" }}
              </button>
            </div>
          </section>
        </form>

        <aside class="paper-margin" aria-label="Paper 边注">
          <p class="paper-eyebrow">Paper identity</p>
          <strong>{{ paper?.code }}</strong>
          <code>{{ paper?.path || "尚未写入磁盘" }}</code>
          <dl>
            <div><dt>创建</dt><dd>{{ paper?.created }}</dd></div>
            <div><dt>更新</dt><dd>{{ paper?.updated }}</dd></div>
          </dl>
        </aside>
      </div>
    </main>
  </div>
</template>

<style scoped>
.paper-shell {
  --canvas: #eceae4;
  --paper: #fffefa;
  --ink: #1e2523;
  --muted: #646b68;
  --accent: #2e5d57;
  --signal: #9a4e3f;
  --rule: #c8c9c2;
  --danger: #a33e3e;
  display: grid;
  grid-template-columns: 72px 260px minmax(0, 1fr);
  min-height: 100vh;
  color: var(--ink);
  background: var(--canvas);
}

button,
input,
textarea {
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

.paper-eyebrow {
  margin: 0;
  color: var(--muted, #646b68);
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.paper-gate {
  display: grid;
  min-height: 100vh;
  padding: 32px;
  place-items: center;
  background: #eceae4;
}

.paper-gate > section {
  width: min(680px, 100%);
  padding: 40px;
  border: 1px solid #c8c9c2;
  background: #fffefa;
}

.paper-gate h1,
.paper-gate blockquote {
  margin: 10px 0 16px;
  font-family: Georgia, "Times New Roman", serif;
  font-size: clamp(2rem, 6vw, 3.5rem);
  font-weight: 500;
  line-height: 1.08;
}

.paper-gate button {
  display: block;
  margin: 24px 0 8px;
  padding: 10px 18px;
  border: 1px solid #1e2523;
  color: #fffefa;
  background: #2e5d57;
}

.paper-gate-error {
  border-top: 4px solid #a33e3e !important;
}

.paper-gate dl {
  margin-top: 24px;
}

.paper-rail {
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

.paper-brand {
  display: grid;
  width: 38px;
  height: 38px;
  border: 1px solid var(--paper);
  place-items: center;
  font-family: Georgia, "Times New Roman", serif;
  font-size: 1.4rem;
}

.paper-destination {
  display: grid;
  width: 52px;
  min-height: 50px;
  place-items: center;
  color: #b9c0bd;
  font-weight: 700;
}

.paper-rail button.paper-destination {
  border: 0;
  padding: 0;
  background: transparent;
}

.paper-destination small {
  font-size: 0.58rem;
  font-weight: 500;
}

.paper-destination.is-active {
  border-left: 3px solid var(--signal);
  color: var(--paper);
  background: #2d3532;
}

.paper-local {
  margin-top: auto;
  font: 0.58rem ui-monospace, SFMono-Regular, Menlo, monospace;
  letter-spacing: 0.12em;
}

.paper-context {
  min-width: 0;
  padding: 28px 20px;
  border-right: 1px solid var(--rule);
  background: #f4f3ee;
}

.paper-context h1,
.paper-workspace h2 {
  margin: 8px 0;
  font-family: Georgia, "Times New Roman", serif;
  font-weight: 500;
}

.paper-context header > p:last-child {
  color: var(--muted);
  font-size: 0.78rem;
}

.new-paper {
  width: 100%;
  margin: 18px 0 28px;
  color: var(--paper);
  background: var(--accent);
}

.paper-context h2 {
  display: flex;
  justify-content: space-between;
  margin: 0 0 10px;
  font-size: 0.78rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.paper-picker {
  display: grid;
  gap: 6px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.paper-picker button {
  display: grid;
  width: 100%;
  gap: 3px;
  border-color: transparent;
  text-align: left;
  background: transparent;
}

.paper-picker button.selected {
  border-color: var(--rule);
  border-left: 3px solid var(--signal);
  background: var(--paper);
}

.paper-picker span,
.paper-picker small,
.empty-list {
  overflow-wrap: anywhere;
  color: var(--muted);
  font: 0.7rem ui-monospace, SFMono-Regular, Menlo, monospace;
}

.paper-workspace {
  min-width: 0;
  padding: 30px clamp(24px, 4vw, 56px) 64px;
}

.paper-workspace-header {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 20px;
  padding-bottom: 18px;
  border-bottom: 1px solid var(--rule);
}

.paper-workspace-header h2 {
  font-size: clamp(2rem, 4vw, 3.2rem);
}

.paper-workspace-header > span {
  color: #2f6b50;
  font-size: 0.78rem;
}

.paper-workspace-header > span.dirty {
  color: var(--signal);
}

.paper-stage {
  display: grid;
  grid-template-columns: minmax(0, 720px) minmax(160px, 220px);
  gap: clamp(24px, 4vw, 52px);
  margin-top: 28px;
}

.paper-editor {
  display: grid;
  gap: 22px;
  padding: 28px;
  border: 1px solid var(--rule);
  border-top: 3px solid var(--signal);
  background: var(--paper);
}

.paper-editor > label,
.highlight-fields label {
  display: grid;
  gap: 7px;
  font-size: 0.82rem;
  font-weight: 650;
}

input,
textarea {
  width: 100%;
  border: 1px solid var(--rule);
  padding: 10px 11px;
  color: var(--ink);
  background: #fff;
}

textarea {
  resize: vertical;
  line-height: 1.55;
}

input[readonly] {
  color: var(--muted);
  background: #f4f3ee;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
}

.initial-copy {
  padding: 16px;
  border-left: 3px solid var(--accent);
  background: #f4f3ee;
}

.initial-copy h3,
.initial-copy p {
  margin: 0;
}

.initial-copy p {
  margin-top: 8px;
  line-height: 1.55;
  white-space: pre-wrap;
}

.paper-highlights {
  min-width: 0;
  margin: 0;
  border: 0;
  padding: 0;
}

.paper-highlights > p {
  margin: 5px 0 14px;
  color: var(--muted);
  font-size: 0.78rem;
}

.paper-highlights ol {
  display: grid;
  gap: 12px;
  margin: 0 0 12px;
  padding: 0;
  list-style: none;
}

.paper-highlights li {
  display: grid;
  grid-template-columns: 34px minmax(0, 1fr);
  gap: 12px;
  padding: 14px 0;
  border-top: 1px solid var(--rule);
}

.highlight-number {
  font: 0.74rem ui-monospace, SFMono-Regular, Menlo, monospace;
}

.highlight-fields {
  display: grid;
  gap: 12px;
}

.highlight-actions {
  display: flex;
  grid-column: 2;
  flex-wrap: wrap;
  gap: 6px;
}

.highlight-actions button {
  padding: 5px 8px;
  border-color: var(--rule);
  font-size: 0.72rem;
}

.paper-error,
.delete-confirm {
  display: grid;
  gap: 10px;
  padding: 14px;
  border: 1px solid var(--danger);
  background: #fff7f4;
}

.paper-error small {
  color: var(--muted);
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
}

.paper-error button {
  justify-self: start;
}

.paper-notice {
  margin: 0;
  color: #2f6b50;
  font-weight: 650;
}

.paper-actions,
.delete-confirm > div {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.primary-action {
  color: var(--paper);
  background: var(--accent);
}

.danger-action {
  color: var(--paper);
  background: var(--danger);
}

.delete-confirm h3,
.delete-confirm p {
  margin: 0;
}

.paper-margin {
  align-self: start;
  padding-left: 16px;
  border-left: 2px solid var(--signal);
}

.paper-margin > strong,
.paper-margin > code {
  display: block;
  margin-top: 10px;
  overflow-wrap: anywhere;
}

.paper-margin > code,
.paper-margin dd {
  font: 0.72rem ui-monospace, SFMono-Regular, Menlo, monospace;
}

.paper-margin dl {
  margin-top: 24px;
}

.paper-margin dl div {
  grid-template-columns: 1fr;
  gap: 3px;
}

@media (max-width: 1100px) {
  .paper-stage {
    grid-template-columns: 1fr;
  }

  .paper-margin {
    order: -1;
  }
}

@media (max-width: 760px) {
  .paper-shell {
    grid-template-columns: 56px minmax(0, 1fr);
  }

  .paper-rail {
    grid-row: 1 / span 2;
  }

  .paper-context {
    border-right: 0;
    border-bottom: 1px solid var(--rule);
  }

  .paper-workspace {
    grid-column: 2;
    padding: 24px 18px 48px;
  }
}

@media (max-width: 520px) {
  .paper-shell {
    display: block;
  }

  .paper-rail {
    position: static;
    min-height: auto;
    flex-direction: row;
    justify-content: space-between;
  }

  .paper-local {
    margin: 0;
  }

  .paper-context {
    padding: 22px 16px;
  }

  .paper-workspace-header {
    align-items: start;
    flex-direction: column;
  }

  .paper-editor {
    padding: 20px 16px;
  }

  .paper-gate {
    padding: 16px;
  }

  .paper-gate > section {
    padding: 24px;
  }
}
</style>

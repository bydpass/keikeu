<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";

const props = defineProps({
  paper: { type: Object, required: true },
  state: { type: String, default: "ready" },
});
const emit = defineEmits(["dirty-change", "save"]);

const typeLabels = { summary: "总结", snapshot: "高光", whisper: "碎碎念" };
const stateMessages = {
  stale: "磁盘内容已变化：草稿保留，但禁止覆盖。",
  repair_required: "Paper 结构需要人工修复；app 不会自动改写损坏文件。",
  index_degraded: "Paper 可继续编辑，但 Library 列表可能过期。",
  commit_unknown: "保存结果未知：草稿与旧基线均已保留，禁止重发保存。",
};
const invalidNameCharacter = /[\p{Cc}\p{Cs}\p{Zl}\p{Zp}]/u;

const draft = ref(null);
const baseline = ref("");
const activeIndex = ref(0);
const advanced = ref(false);
const fieldErrors = ref({});
const pageTitleInput = ref(null);
const contentInput = ref(null);
const deleteDialog = ref(null);
const cancelDeleteButton = ref(null);
const cursorKnown = ref(false);
const lastCursor = ref(0);
let nextUiKey = 1;

function normalizedTags(value) {
  const tags = [];
  for (const line of value.split("\n")) {
    const tag = line.trim();
    if (tag && !tags.includes(tag)) {
      tags.push(tag);
    }
  }
  return tags;
}

function editableProjection(value) {
  return {
    display_name: value.display_name?.trim() || null,
    tags: normalizedTags(value.tags_text),
    pages: value.pages.map(({ name, content, type }) => ({
      name: name?.trim() || null,
      content,
      type,
    })),
  };
}

function loadPaper(paper) {
  draft.value = {
    code: paper.code,
    display_name: paper.display_name ?? "",
    tags_text: (paper.tags ?? []).join("\n"),
    pages: paper.pages.map((page) => ({ ...page, ui_key: nextUiKey++ })),
  };
  baseline.value = JSON.stringify(editableProjection(draft.value));
  activeIndex.value = 0;
  cursorKnown.value = false;
  fieldErrors.value = {};
}

watch(() => props.paper, loadPaper, { immediate: true });

const activePage = computed(() => draft.value.pages[activeIndex.value]);
const dirty = computed(
  () => JSON.stringify(editableProjection(draft.value)) !== baseline.value,
);
const summaryIndex = computed(() =>
  draft.value.pages.findIndex((page) => page.type === "summary"),
);
const saveBlocked = computed(() =>
  ["stale", "repair_required", "commit_unknown"].includes(props.state),
);

watch(dirty, (value) => emit("dirty-change", value), { immediate: true });

function codePointLength(value) {
  return [...value].length;
}

function validateName(value, label) {
  const normalized = value.trim();
  if (codePointLength(normalized) > 200) {
    return `${label}最多 200 个 Unicode 字符。`;
  }
  if (invalidNameCharacter.test(normalized)) {
    return `${label}不能包含控制或分行字符。`;
  }
  return null;
}

function validate() {
  const errors = { pages: {} };
  const displayNameError = validateName(draft.value.display_name, "Paper 名称");
  if (displayNameError) {
    errors.display_name = displayNameError;
  }
  const tags = normalizedTags(draft.value.tags_text);
  const invalidTag = tags.find((tag) => invalidNameCharacter.test(tag));
  if (invalidTag) {
    errors.tags = "Tags 必须是单行文字。";
  }
  let summaries = 0;
  draft.value.pages.forEach((page, index) => {
    const pageErrors = {};
    const nameError = validateName(page.name ?? "", `第 ${index + 1} 页标题`);
    if (nameError) {
      pageErrors.name = nameError;
    }
    if (!(page.name?.trim() || page.content.trim())) {
      pageErrors.content = `第 ${index + 1} 页需要标题或正文。`;
    }
    if (page.type === "summary") {
      summaries += 1;
    }
    if (Object.keys(pageErrors).length) {
      errors.pages[index] = pageErrors;
    }
  });
  if (summaries > 1) {
    errors.summary = "一份 Paper 最多一页标为总结。";
  }
  fieldErrors.value = errors;
  return !errors.display_name && !errors.tags && !errors.summary && !Object.keys(errors.pages).length;
}

function save() {
  if (saveBlocked.value || !validate()) {
    return;
  }
  emit("save", { code: draft.value.code, ...editableProjection(draft.value) });
}

function handleShortcut(event) {
  if (event.metaKey && event.key.toLowerCase() === "s") {
    event.preventDefault();
    save();
  }
}

function selectPage(index) {
  activeIndex.value = index;
  cursorKnown.value = false;
  nextTick(() => pageTitleInput.value?.focus());
}

function rememberCursor() {
  if (!contentInput.value) {
    return;
  }
  lastCursor.value = contentInput.value.selectionStart ?? activePage.value.content.length;
  cursorKnown.value = true;
}

function addPage() {
  const page = activePage.value;
  const cut = cursorKnown.value
    ? Math.max(0, Math.min(lastCursor.value, page.content.length))
    : page.content.length;
  const moved = page.content.slice(cut);
  page.content = page.content.slice(0, cut);
  draft.value.pages.splice(activeIndex.value + 1, 0, {
    ui_key: nextUiKey++,
    name: null,
    content: moved,
    type: null,
  });
  activeIndex.value += 1;
  cursorKnown.value = false;
  nextTick(() => pageTitleInput.value?.focus());
}

function askDelete() {
  if (typeof deleteDialog.value?.showModal === "function") {
    deleteDialog.value.showModal();
  } else if (deleteDialog.value) {
    deleteDialog.value.open = true;
  }
  nextTick(() => cancelDeleteButton.value?.focus());
}

function closeDelete() {
  if (typeof deleteDialog.value?.close === "function") {
    deleteDialog.value.close();
  } else if (deleteDialog.value) {
    deleteDialog.value.open = false;
  }
}

function deletePage() {
  if (draft.value.pages.length === 1) {
    draft.value.pages = [{ ui_key: nextUiKey++, name: null, content: "", type: null }];
    activeIndex.value = 0;
  } else {
    draft.value.pages.splice(activeIndex.value, 1);
    activeIndex.value = Math.min(activeIndex.value, draft.value.pages.length - 1);
  }
  cursorKnown.value = false;
  closeDelete();
  nextTick(() => pageTitleInput.value?.focus());
}

function onBeforeUnload(event) {
  if (dirty.value) {
    event.preventDefault();
    event.returnValue = "";
  }
}

onMounted(() => window.addEventListener("beforeunload", onBeforeUnload));
onBeforeUnmount(() => window.removeEventListener("beforeunload", onBeforeUnload));
</script>

<template>
  <section class="paper-v4-workbench" @keydown="handleShortcut">
    <p v-if="stateMessages[state]" :class="['workbench-state', `state-${state}`]" role="status">
      {{ stateMessages[state] }}
    </p>

    <header class="paper-meta-bar">
      <div class="paper-code">
        <span>Paper</span>
        <strong>{{ draft.code }}</strong>
      </div>
      <label>
        <span>Paper 名称</span>
        <input v-model="draft.display_name" aria-describedby="paper-name-help">
        <small id="paper-name-help">
          {{ codePointLength(draft.display_name.trim()) }} / 200
          <b v-if="fieldErrors.display_name">· {{ fieldErrors.display_name }}</b>
        </small>
      </label>
      <label>
        <span>Tags · 每行一个</span>
        <textarea v-model="draft.tags_text" rows="2" placeholder="夜车&#10;重逢,旧友" />
        <small v-if="fieldErrors.tags">{{ fieldErrors.tags }}</small>
      </label>
    </header>

    <nav class="page-navigation" aria-label="Paper 页面">
      <button
        v-for="(page, index) in draft.pages"
        :key="page.ui_key"
        type="button"
        :aria-current="index === activeIndex ? 'page' : undefined"
        @click="selectPage(index)"
      >
        {{ index + 1 }}
        <span v-if="page.type">{{ typeLabels[page.type] }}</span>
      </button>
      <span>{{ activeIndex + 1 }} / {{ draft.pages.length }}</span>
      <button
        type="button"
        class="mode-toggle"
        :aria-expanded="advanced"
        @click="advanced = !advanced"
      >
        {{ advanced ? "收起进一步" : "进一步" }}
      </button>
    </nav>

    <article class="card-page">
      <span v-if="activePage.type" class="type-badge">{{ typeLabels[activePage.type] }}</span>
      <label class="page-title-field">
        <span>页面标题</span>
        <input
          ref="pageTitleInput"
          v-model="activePage.name"
          placeholder="给这一页一个名字（可空）"
        >
        <small>
          {{ codePointLength((activePage.name ?? "").trim()) }} / 200
          <b v-if="fieldErrors.pages?.[activeIndex]?.name">
            · {{ fieldErrors.pages[activeIndex].name }}
          </b>
        </small>
      </label>

      <label class="page-content-field">
        <span>正文</span>
        <textarea
          ref="contentInput"
          v-model="activePage.content"
          rows="14"
          placeholder="写下任何你想留下的文字……"
          @focus="rememberCursor"
          @click="rememberCursor"
          @keyup="rememberCursor"
          @select="rememberCursor"
          @input="rememberCursor"
        />
        <small v-if="fieldErrors.pages?.[activeIndex]?.content">
          {{ fieldErrors.pages[activeIndex].content }}
        </small>
      </label>

      <section v-if="advanced" class="advanced-panel" aria-label="进一步模式">
        <label>
          <span>页面类型</span>
          <select v-model="activePage.type">
            <option :value="null">不标记</option>
            <option
              value="summary"
              :disabled="summaryIndex !== -1 && summaryIndex !== activeIndex"
            >
              总结
            </option>
            <option value="snapshot">高光</option>
            <option value="whisper">碎碎念</option>
          </select>
        </label>
        <p v-if="summaryIndex !== -1 && summaryIndex !== activeIndex">
          已有一页标为总结；本页的“总结”选项保持可见但不可选。
        </p>
        <p v-if="fieldErrors.summary">{{ fieldErrors.summary }}</p>
      </section>

      <footer class="card-actions">
        <button type="button" :disabled="saveBlocked" @click="save">保存</button>
        <button type="button" class="danger-action" @click="askDelete">删除本页</button>
        <button type="button" @click="addPage">加一页</button>
      </footer>
    </article>

    <p class="draft-state" aria-live="polite">
      {{ dirty ? "草稿有未保存修改" : "草稿与已保存基线一致" }}
      <span v-if="state === 'index_degraded'">· 只允许显式重建 Index</span>
    </p>

    <dialog ref="deleteDialog" class="delete-page-dialog" @cancel="closeDelete">
      <h2>删除当前页？</h2>
      <p>只有下一次整体保存成功后，这次删除才会写入 Paper。</p>
      <div>
        <button ref="cancelDeleteButton" type="button" @click="closeDelete">取消</button>
        <button type="button" class="danger-action" @click="deletePage">确认删除</button>
      </div>
    </dialog>
  </section>
</template>

<style scoped>
.paper-v4-workbench {
  width: min(920px, 100%);
  margin: 0 auto;
}

button,
input,
textarea,
select {
  font: inherit;
}

.workbench-state {
  margin: 0 0 16px;
  padding: 10px 14px;
  border-left: 4px solid var(--signal);
  background: var(--paper);
  font-size: 0.82rem;
}

.state-stale,
.state-repair_required,
.state-commit_unknown {
  border-left-color: var(--danger);
  background: var(--danger-soft);
}

.paper-meta-bar {
  display: grid;
  grid-template-columns: 150px minmax(220px, 1fr) minmax(220px, 0.8fr);
  gap: 18px;
  align-items: end;
  padding: 16px 20px;
  border: 1px solid var(--rule);
  border-bottom: 0;
  background: var(--soft);
}

.paper-meta-bar label,
.page-title-field,
.page-content-field,
.advanced-panel label {
  display: grid;
  gap: 6px;
  color: var(--muted);
  font-size: 0.72rem;
  font-weight: 700;
}

.paper-meta-bar input,
.paper-meta-bar textarea,
.page-title-field input,
.page-content-field textarea,
.advanced-panel select {
  width: 100%;
  border: 1px solid var(--rule);
  border-radius: var(--radius-xs);
  color: var(--ink);
  background: var(--field);
}

.paper-meta-bar input,
.page-title-field input,
.advanced-panel select {
  min-height: 42px;
  padding: 8px 10px;
}

.paper-meta-bar textarea {
  padding: 8px 10px;
  resize: vertical;
}

.paper-meta-bar small,
.page-title-field small,
.page-content-field small {
  min-height: 1.2em;
  color: var(--meta);
  font-weight: 400;
}

.paper-meta-bar b,
.page-title-field b,
.page-content-field small {
  color: var(--danger);
}

.paper-code {
  align-self: center;
}

.paper-code span {
  display: block;
  color: var(--meta);
  font-size: 0.66rem;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.paper-code strong {
  display: block;
  margin-top: 5px;
  font: 0.78rem var(--font-mono);
}

.page-navigation {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 7px;
  padding: 11px 18px;
  border: 1px solid var(--rule);
  background: var(--paper);
}

.page-navigation button {
  min-width: 38px;
  min-height: 36px;
  padding: 5px 9px;
  border: 1px solid var(--rule);
  border-radius: 999px;
  color: var(--ink);
  background: transparent;
  cursor: pointer;
}

.page-navigation button[aria-current="page"] {
  border-color: var(--signal);
  color: var(--paper);
  background: var(--signal);
}

.page-navigation button span {
  margin-left: 3px;
  font-size: 0.62rem;
}

.page-navigation > span {
  margin-left: 4px;
  color: var(--meta);
  font: 0.68rem var(--font-mono);
}

.page-navigation .mode-toggle {
  margin-left: auto;
  border-radius: var(--radius-xs);
}

.card-page {
  position: relative;
  display: grid;
  min-height: 570px;
  gap: 22px;
  padding: 42px 54px 28px;
  border: 1px solid var(--rule);
  border-top: 4px solid var(--signal);
  background: var(--paper);
  box-shadow: 0 18px 45px color-mix(in srgb, var(--ink) 10%, transparent);
}

.type-badge {
  position: absolute;
  top: 17px;
  right: 20px;
  padding: 4px 9px;
  border: 1px solid var(--signal);
  color: var(--signal);
  font-size: 0.68rem;
  font-weight: 750;
  letter-spacing: 0.08em;
}

.page-title-field input {
  border-width: 0 0 1px;
  border-radius: 0;
  background: transparent;
  font: 500 clamp(1.6rem, 3vw, 2.4rem) var(--font-display);
}

.page-content-field {
  min-height: 0;
}

.page-content-field textarea {
  min-height: 300px;
  flex: 1;
  padding: 18px;
  font: 1rem/1.75 var(--font-body);
  resize: vertical;
}

.advanced-panel {
  display: grid;
  grid-template-columns: minmax(180px, 260px) minmax(0, 1fr);
  gap: 12px 20px;
  padding: 16px;
  border: 1px dashed var(--rule);
  background: var(--soft);
}

.advanced-panel p {
  margin: 24px 0 0;
  color: var(--meta);
  font-size: 0.76rem;
}

.card-actions {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 10px;
  padding-top: 18px;
  border-top: 1px solid var(--rule);
}

.card-actions button,
.delete-page-dialog button {
  min-height: 44px;
  padding: 9px 14px;
  border: 1px solid var(--ink);
  border-radius: var(--radius-xs);
  color: var(--ink);
  background: transparent;
  cursor: pointer;
}

.card-actions button:first-child {
  color: var(--paper);
  background: var(--signal);
}

.card-actions .danger-action,
.delete-page-dialog .danger-action {
  border-color: var(--danger);
  color: var(--danger);
}

.card-actions button:disabled {
  cursor: not-allowed;
  opacity: 0.45;
}

.draft-state {
  margin: 12px 0 0;
  color: var(--meta);
  font: 0.7rem var(--font-mono);
  text-align: right;
}

.delete-page-dialog {
  width: min(430px, calc(100% - 32px));
  padding: 26px;
  border: 1px solid var(--ink);
  color: var(--ink);
  background: var(--paper);
}

.delete-page-dialog::backdrop {
  background: color-mix(in srgb, var(--ink) 56%, transparent);
}

.delete-page-dialog h2 {
  margin: 0;
  font: 500 1.5rem var(--font-display);
}

.delete-page-dialog p {
  color: var(--muted);
}

.delete-page-dialog div {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 24px;
}

@media (max-width: 920px) {
  .paper-meta-bar {
    grid-template-columns: 1fr 1fr;
  }

  .paper-code {
    grid-column: 1 / -1;
  }

  .card-page {
    padding-inline: 30px;
  }
}

@media (max-width: 620px) {
  .paper-meta-bar {
    grid-template-columns: 1fr;
  }

  .paper-code {
    grid-column: auto;
  }

  .advanced-panel,
  .card-actions {
    grid-template-columns: 1fr;
  }

  .page-navigation .mode-toggle {
    width: 100%;
    margin-left: 0;
  }
}
</style>

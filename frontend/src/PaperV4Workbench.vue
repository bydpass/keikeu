<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, useId, watch } from "vue";

import { translate } from "./locale.js";
import { formatTagsCsv, parseTagsCsv } from "./tagsCsv.js";

const props = defineProps({
  paper: { type: Object, required: true },
  rawDraft: { type: Object, default: null },
  locale: { type: String, default: "zh-CN" },
  baselineEditable: { type: Object, default: undefined },
  state: { type: String, default: "ready" },
  saving: { type: Boolean, default: false },
  allowInputDuringSave: { type: Boolean, default: false },
  canDeleteWholePaper: { type: Boolean, default: false },
});
const emit = defineEmits(["dirty-change", "raw-change", "save", "whole-delete"]);

const t = (text) => translate(props.locale, text);
const typeLabels = computed(() => ({ summary: t("总结"), snapshot: t("高光"), whisper: t("碎碎念") }));
const stateMessages = computed(() => ({
  stale: t("磁盘内容已变化：草稿保留，但禁止覆盖。"),
  repair_required: t("Paper 结构需要人工修复；app 不会自动改写损坏文件。"),
  index_degraded: t("Paper 可继续编辑，但 Library 列表可能过期。"),
  commit_unknown: t("保存结果未知：草稿与旧基线均已保留，禁止重发保存。"),
}));
const invalidNameCharacter = /[\p{Cc}\p{Cs}\p{Zl}\p{Zp}]/u;

const draft = ref(null);
const baseline = ref("");
const activeIndex = ref(0);
const advanced = ref(false);
const fieldErrors = ref({});
const pageTitleInput = ref(null);
const contentInput = ref(null);
const pageNavigation = ref(null);
const deleteDialog = ref(null);
const cancelDeleteButton = ref(null);
const detailsOpen = ref(false);
const detailsPopoverId = `paper-details-popover-${useId()}`;
const cursorKnown = ref(false);
const lastCursor = ref(0);
let nextUiKey = 1;

function editableProjection(value, tags = parseTagsCsv(value.tags_text).tags) {
  return {
    display_name: value.display_name?.trim() || null,
    tags,
    pages: value.pages.map(({ name, content, type }) => ({
      name: name?.trim() || null,
      content,
      type,
    })),
  };
}

function loadPaper() {
  const paper = props.paper;
  draft.value = {
    code: paper.code,
    display_name: paper.display_name ?? "",
    tags_text: formatTagsCsv(paper.tags ?? []),
    pages: paper.pages.map((page) => ({ ...page, ui_key: nextUiKey++ })),
  };
  baseline.value = props.baselineEditable === undefined
    ? JSON.stringify(editableProjection(draft.value))
    : props.baselineEditable === null
      ? "__missing_paper__"
      : JSON.stringify(props.baselineEditable);
  if (props.rawDraft) {
    draft.value = JSON.parse(JSON.stringify(props.rawDraft));
    draft.value.pages = draft.value.pages.map((page) => ({ ...page, ui_key: nextUiKey++ }));
  }
  activeIndex.value = 0;
  cursorKnown.value = false;
  fieldErrors.value = {};
  centerActivePage();
}

watch(
  [() => props.paper, () => props.baselineEditable],
  loadPaper,
  { immediate: true },
);

const activePage = computed(() => draft.value.pages[activeIndex.value]);
const parsedTags = computed(() => parseTagsCsv(draft.value.tags_text));
const tagInputError = computed(() => {
  if (!parsedTags.value.ok) return t(parsedTags.value.error);
  return parsedTags.value.tags.some((tag) => invalidNameCharacter.test(tag))
    ? t("Tags 必须是单行文字。")
    : null;
});
const dirty = computed(() => (
  !parsedTags.value.ok
  || JSON.stringify(editableProjection(draft.value, parsedTags.value.tags)) !== baseline.value
));
const summaryIndex = computed(() =>
  draft.value.pages.findIndex((page) => page.type === "summary"),
);
const saveBlocked = computed(() =>
  props.saving
  || Boolean(tagInputError.value)
  || ["stale", "repair_required", "commit_unknown"].includes(props.state),
);

watch(draft, (value) => emit("raw-change", JSON.parse(JSON.stringify(value))), { deep: true, immediate: true });

watch(dirty, (value) => emit("dirty-change", value), { immediate: true });

function codePointLength(value) {
  return [...value].length;
}

function validateName(value, label) {
  const normalized = value.trim();
  if (codePointLength(normalized) > 200) {
    return props.locale === "en" ? `${label}: at most 200 Unicode characters.` : `${label}最多 200 个 Unicode 字符。`;
  }
  if (invalidNameCharacter.test(normalized)) {
    return props.locale === "en" ? `${label}: control and line-separator characters are not allowed.` : `${label}不能包含控制或分行字符。`;
  }
  return null;
}

function validate() {
  const errors = { pages: {} };
  const displayNameError = validateName(draft.value.display_name, t("Paper 名称"));
  if (displayNameError) {
    errors.display_name = displayNameError;
  }
  if (tagInputError.value) errors.tags = tagInputError.value;
  let summaries = 0;
  draft.value.pages.forEach((page, index) => {
    const pageErrors = {};
    const nameError = validateName(page.name ?? "", props.locale === "en" ? `Page ${index + 1} title` : `第 ${index + 1} 页标题`);
    if (nameError) {
      pageErrors.name = nameError;
    }
    if (!(page.name?.trim() || page.content.trim())) {
      pageErrors.content = props.locale === "en" ? `Page ${index + 1} needs a title or body.` : `第 ${index + 1} 页需要标题或正文。`;
    }
    if (page.type === "summary") {
      summaries += 1;
    }
    if (Object.keys(pageErrors).length) {
      errors.pages[index] = pageErrors;
    }
  });
  if (summaries > 1) {
    errors.summary = t("一份 Paper 最多一页标为总结。");
  }
  fieldErrors.value = errors;
  return !errors.display_name && !errors.tags && !errors.summary && !Object.keys(errors.pages).length;
}

function save() {
  if (saveBlocked.value || !validate()) {
    return;
  }
  emit("save", {
    code: draft.value.code,
    ...editableProjection(draft.value, parsedTags.value.tags),
  });
}

function handleShortcut(event) {
  if (
    !event.isComposing
    && event.keyCode !== 229
    && event.metaKey
    && event.key.toLowerCase() === "s"
  ) {
    event.preventDefault();
    save();
  }
}

function centerActivePage() {
  nextTick(() => {
    const activeButton = pageNavigation.value?.querySelector('[aria-current="page"]');
    if (typeof activeButton?.scrollIntoView === "function") {
      activeButton.scrollIntoView({ inline: "center", block: "nearest" });
    }
  });
}

function selectPage(index) {
  activeIndex.value = index;
  cursorKnown.value = false;
  centerActivePage();
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
  centerActivePage();
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
  centerActivePage();
  nextTick(() => pageTitleInput.value?.focus());
}

function handleDetailsToggle(event) {
  detailsOpen.value = event.newState === "open";
}

function onBeforeUnload(event) {
  if (dirty.value) {
    event.preventDefault();
    event.returnValue = "";
  }
}

onMounted(() => {
  window.addEventListener("beforeunload", onBeforeUnload);
});
onBeforeUnmount(() => {
  window.removeEventListener("beforeunload", onBeforeUnload);
});
</script>

<template>
  <section class="paper-v4-workbench" :lang="locale" @keydown="handleShortcut">
    <p v-if="stateMessages[state]" :class="['workbench-state', `state-${state}`]" role="status">
      {{ stateMessages[state] }}
    </p>

    <header class="paper-meta-bar" aria-label="Paper context">
      <div class="paper-name-row">
        <label class="paper-name-field">
          <span class="field-label">{{ t("Paper 名称") }}</span>
          <input
            v-model="draft.display_name"
            class="paper-name-input"
            aria-describedby="paper-name-help"
            :aria-invalid="fieldErrors.display_name ? 'true' : undefined"
            :readonly="saving && !allowInputDuringSave"
          >
          <small
            id="paper-name-help"
            class="field-help"
            :class="{ 'sr-only': !fieldErrors.display_name }"
          >
            <span class="sr-only">
              {{ codePointLength(draft.display_name.trim()) }} / 200
            </span>
            <b v-if="fieldErrors.display_name" role="alert">{{ fieldErrors.display_name }}</b>
          </small>
        </label>

        <div class="paper-context-tools" aria-live="polite">
          <span>{{ draft.pages.length }} {{ t("页") }}</span>
          <strong v-if="saving">{{ t("正在保存") }}</strong>
          <button
            type="button"
            class="paper-details-trigger"
            :popovertarget="detailsPopoverId"
            aria-haspopup="dialog"
            :aria-expanded="detailsOpen"
            :disabled="saving"
          >
            {{ t("详情") }} <span aria-hidden="true">{{ detailsOpen ? "−" : "+" }}</span>
          </button>
        </div>
      </div>

      <label class="paper-tags-field">
        <span class="field-label">{{ t("Tags（逗号分隔）") }}</span>
        <input
          v-model="draft.tags_text"
          class="paper-tags-input"
          :aria-describedby="tagInputError ? 'paper-tags-error' : undefined"
          :aria-invalid="tagInputError ? 'true' : undefined"
          autocomplete="off"
          autocapitalize="none"
          autocorrect="off"
          :placeholder="t('夜车, 重逢, 旧友')"
          :readonly="saving && !allowInputDuringSave"
          spellcheck="false"
        >
        <small
          v-if="tagInputError"
          id="paper-tags-error"
          class="paper-tags-error"
          role="alert"
        >{{ tagInputError }}</small>
      </label>

      <aside
        :id="detailsPopoverId"
        class="paper-details-popover keikeu-detail-popover"
        popover="auto"
        role="dialog"
        :aria-label="t('Paper 详情')"
        @toggle="handleDetailsToggle"
      >
        <header>
          <strong>{{ t("Paper 详情") }}</strong>
          <button
            type="button"
            :popovertarget="detailsPopoverId"
            popovertargetaction="hide"
            :aria-label="t('关闭 Paper 详情')"
          >{{ t("关闭") }}</button>
        </header>
        <dl>
          <div class="paper-code">
            <dt>Code</dt>
            <dd><strong>{{ draft.code }}</strong></dd>
          </div>
          <div>
            <dt>{{ t("路径") }}</dt>
            <dd><code>{{ paper.path || t("尚未写盘") }}</code></dd>
          </div>
          <div>
            <dt>{{ t("创建时间") }}</dt>
            <dd><time :datetime="paper.created">{{ paper.created }}</time></dd>
          </div>
          <div>
            <dt>{{ t("更新时间") }}</dt>
            <dd><time :datetime="paper.updated">{{ paper.updated }}</time></dd>
          </div>
        </dl>
        <button
          v-if="canDeleteWholePaper"
          type="button"
          class="whole-delete danger-action"
          :popovertarget="detailsPopoverId"
          popovertargetaction="hide"
          :disabled="saving"
          @click="emit('whole-delete')"
        >
          {{ t("整份移入废纸篓") }}
        </button>
      </aside>
    </header>

    <nav ref="pageNavigation" class="page-navigation" :aria-label="t('Paper 页面')">
      <button
        v-for="(page, index) in draft.pages"
        :key="page.ui_key"
        type="button"
        :aria-current="index === activeIndex ? 'page' : undefined"
        :aria-label="`${locale === 'en' ? `Page ${index + 1}` : `第 ${index + 1} 页`}：${page.name || typeLabels[page.type] || t('未命名')}`"
        :disabled="saving"
        @click="selectPage(index)"
      >
        <span class="page-number">{{ String(index + 1).padStart(2, "0") }}</span>
        <span class="page-tab-title">{{ page.name || typeLabels[page.type] || t("未命名") }}</span>
      </button>
    </nav>

    <article class="card-page">
      <p class="current-page-label">
        {{ t("当前页") }} · {{ typeLabels[activePage.type] || t("未标记") }}
      </p>
      <label class="page-title-field">
        <span class="sr-only">{{ t("页面标题") }}</span>
        <input
          ref="pageTitleInput"
          v-model="activePage.name"
          aria-describedby="page-title-help"
          :aria-invalid="fieldErrors.pages?.[activeIndex]?.name ? 'true' : undefined"
          :placeholder="t('给这一页一个名字（可空）')"
          :readonly="saving && !allowInputDuringSave"
        >
        <small
          id="page-title-help"
          class="field-help"
          :class="{ 'sr-only': !fieldErrors.pages?.[activeIndex]?.name }"
        >
          <span class="sr-only">
            {{ codePointLength((activePage.name ?? "").trim()) }} / 200
          </span>
          <b v-if="fieldErrors.pages?.[activeIndex]?.name">
            {{ fieldErrors.pages[activeIndex].name }}
          </b>
        </small>
      </label>

      <div class="editor-body-header">
        <span>{{ t("正文 · Markdown") }}</span>
        <button
          type="button"
          class="mode-toggle"
          :aria-expanded="advanced"
          :disabled="saving"
          @click="advanced = !advanced"
        >
          {{ advanced ? t("收起") : t("进一步") }} <span aria-hidden="true">{{ advanced ? "−" : "+" }}</span>
        </button>
      </div>

      <section v-if="advanced" class="advanced-panel" :aria-label="t('进一步模式')">
        <label>
          <span>{{ t("页面类型") }}</span>
          <select v-model="activePage.type" :disabled="saving">
            <option :value="null">{{ t("不标记") }}</option>
            <option
              value="summary"
              :disabled="summaryIndex !== -1 && summaryIndex !== activeIndex"
            >
              {{ t("总结") }}
            </option>
            <option value="snapshot">{{ t("高光") }}</option>
            <option value="whisper">{{ t("碎碎念") }}</option>
          </select>
        </label>
        <p v-if="summaryIndex !== -1 && summaryIndex !== activeIndex">
          {{ t("已有一页标为总结；本页的“总结”选项保持可见但不可选。") }}
        </p>
        <p v-if="fieldErrors.summary">{{ fieldErrors.summary }}</p>
      </section>

      <label class="page-content-field">
        <span class="sr-only">{{ t("正文 · Markdown") }}</span>
        <textarea
          ref="contentInput"
          v-model="activePage.content"
          rows="10"
          :placeholder="t('写下任何你想留下的文字……')"
          :readonly="saving && !allowInputDuringSave"
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

      <footer class="card-actions">
        <button type="button" class="danger-action" :disabled="saving" @click="askDelete">
          {{ t("删除本页") }}
        </button>
        <button type="button" :disabled="saving" @click="addPage">{{ t("加一页") }}</button>
        <button type="button" class="save-action" :disabled="saveBlocked" @click="save">
          {{ t("保存") }}
        </button>
      </footer>
    </article>

    <dialog ref="deleteDialog" class="delete-page-dialog" @cancel="closeDelete">
      <h2>{{ t("删除当前页？") }}</h2>
      <p>{{ t("只有下一次整体保存成功后，这次删除才会写入 Paper。") }}</p>
      <div>
        <button ref="cancelDeleteButton" type="button" :disabled="saving" @click="closeDelete">
          {{ t("取消") }}
        </button>
        <button type="button" class="danger-action" :disabled="saving" @click="deletePage">
          {{ t("确认删除") }}
        </button>
      </div>
    </dialog>
  </section>
</template>

<style scoped>
.paper-v4-workbench {
  width: min(960px, 100%);
  margin: 0 auto;
}

button,
input,
textarea,
select {
  font: inherit;
}

.workbench-state {
  margin: 0 0 12px;
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
  position: relative;
  display: grid;
  gap: 12px;
}

.paper-name-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 16px;
  align-items: end;
}

.paper-name-field,
.page-title-field,
.page-content-field {
  display: block;
  min-width: 0;
  color: var(--muted);
  font-size: 0.72rem;
  font-weight: 700;
}

.advanced-panel label {
  display: grid;
  gap: 4px;
  min-width: 0;
  color: var(--muted);
  font-size: 0.72rem;
  font-weight: 700;
}

.field-label,
.editor-body-header,
.current-page-label {
  display: block;
  color: var(--meta);
  font-size: 0.7rem;
  font-weight: 750;
  letter-spacing: 0.04em;
}

.paper-name-input,
.paper-tags-input,
.page-title-field input,
.page-content-field textarea {
  width: 100%;
  border: 0;
  border-bottom: 1px solid var(--rule);
  border-radius: 0;
  color: var(--ink);
  background: transparent;
  caret-color: var(--accent);
}

.paper-name-input,
.paper-tags-input,
.page-title-field input {
  min-height: 44px;
  padding: 4px 0;
}

.paper-name-input {
  padding-block-end: 6px;
  font: 500 2rem/2.5rem var(--font-opus);
  letter-spacing: -0.015em;
}

.paper-tags-field {
  display: grid;
  grid-template-columns: 112px minmax(0, 1fr);
  min-height: 44px;
  align-items: baseline;
  column-gap: 12px;
  border-bottom: 1px solid var(--rule);
  color: var(--muted);
  font-size: 0.72rem;
  font-weight: 700;
}

.paper-tags-input {
  min-height: 43px;
  padding-block: 8px;
  border-bottom: 0;
}

.field-help,
.paper-tags-error,
.page-content-field small {
  grid-column: 1 / -1;
  margin: 0;
  color: var(--meta);
  font-size: 0.72rem;
  font-weight: 400;
}

.field-help:empty {
  display: none;
}

.field-help b,
.paper-tags-error,
.page-content-field small {
  color: var(--danger);
}

.paper-context-tools {
  display: flex;
  gap: 10px;
  min-height: 44px;
  align-items: center;
  justify-content: flex-end;
  color: var(--meta);
  font-size: 0.72rem;
  white-space: nowrap;
}

.paper-context-tools strong {
  color: var(--signal);
}

.paper-details-trigger,
.mode-toggle {
  min-height: 44px;
  padding: 6px 8px;
  border: 0;
  color: var(--muted);
  background: transparent;
  cursor: pointer;
}

.paper-details-popover {
  --details-top: 152px;
}

.paper-details-popover dl > div:first-child {
  padding-top: 0;
  border-top: 0;
}

.paper-details-popover dt {
  color: var(--meta);
  font-size: 0.68rem;
}

.paper-details-popover dd {
  margin: 0;
  overflow-wrap: anywhere;
  color: var(--ink);
  font: 0.76rem var(--font-mono);
}

.whole-delete {
  min-height: 44px;
  margin-top: 14px;
  padding: 7px 10px;
  border: 1px solid var(--danger);
  border-radius: var(--radius-xs);
  color: var(--danger);
  background: transparent;
  cursor: pointer;
}

.page-navigation {
  display: grid;
  grid-auto-columns: calc((100% - 32px) / 3);
  grid-auto-flow: column;
  column-gap: 16px;
  width: 100%;
  min-width: 0;
  height: 60px;
  margin-top: 16px;
  overflow-x: scroll;
  overflow-y: hidden;
  border-bottom: 1px solid var(--rule);
  overscroll-behavior-inline: contain;
  scrollbar-color: var(--rule) transparent;
  scrollbar-gutter: stable;
  scrollbar-width: thin;
  scroll-snap-type: x mandatory;
}

.page-navigation::-webkit-scrollbar {
  display: block;
  height: 6px;
}

.page-navigation::-webkit-scrollbar-track {
  background: transparent;
}

.page-navigation::-webkit-scrollbar-thumb {
  border-radius: 999px;
  background: var(--rule);
}

.page-navigation::before,
.page-navigation::after {
  content: "";
}

.page-navigation button {
  display: grid;
  grid-template-columns: 26px minmax(0, 1fr);
  gap: 10px;
  min-width: 0;
  min-height: 52px;
  align-items: center;
  padding: 4px 12px 2px 0;
  border: 0;
  border-bottom: 2px solid transparent;
  color: var(--muted);
  background: transparent;
  cursor: pointer;
  scroll-snap-align: center;
  text-align: left;
}

.page-navigation button[aria-current="page"] {
  border-bottom-color: var(--accent);
  color: var(--ink);
}

.page-number {
  color: var(--accent);
  font: 700 0.66rem var(--font-mono);
}

.page-tab-title {
  overflow: hidden;
  font-size: 0.75rem;
  font-weight: 700;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.card-page {
  display: flex;
  min-height: 548px;
  flex-direction: column;
  padding-top: 20px;
}

.current-page-label {
  margin: 0 0 8px;
  color: var(--accent);
}

.page-title-field input {
  min-height: 48px;
  padding-block-end: 8px;
  font: 500 1.875rem/2.375rem var(--font-opus);
  letter-spacing: -0.015em;
}

.editor-body-header {
  display: flex;
  min-height: 44px;
  align-items: center;
  justify-content: space-between;
  margin-top: 8px;
}

.mode-toggle {
  color: var(--meta);
  font-size: 0.72rem;
}

.advanced-panel {
  display: grid;
  grid-template-columns: minmax(150px, 220px) minmax(0, 1fr);
  gap: 10px 16px;
  padding: 12px;
  border-left: 2px solid var(--rule);
  background: var(--canvas);
}

.advanced-panel select {
  min-height: 44px;
  padding: 6px 10px;
  border: 1px solid var(--rule);
  border-radius: var(--radius-xs);
  color: var(--ink);
  background: var(--field);
}

.advanced-panel p {
  margin: 22px 0 0;
  color: var(--meta);
  font-size: 0.76rem;
}

.page-content-field {
  display: flex;
  min-height: 300px;
  flex: 1;
  flex-direction: column;
}

.page-content-field textarea {
  width: min(72ch, 100%);
  min-height: 300px;
  height: 300px;
  flex: 1;
  padding: 12px 0 32px;
  font: 1rem/1.75 var(--font-body);
  resize: vertical;
}

.paper-name-field:focus-within .field-label,
.paper-tags-field:focus-within .field-label,
.editor-body-header:has(+ .advanced-panel) {
  color: var(--accent);
}

.paper-name-input:focus-visible,
.paper-tags-input:focus-visible,
.page-title-field input:focus-visible,
.page-content-field textarea:focus-visible {
  outline: 2px solid transparent;
  outline-offset: 0;
  border-bottom-color: var(--rule);
  background: color-mix(in srgb, var(--accent) 4%, transparent);
}

.card-actions {
  display: grid;
  grid-template-columns: minmax(72px, auto) 104px 124px;
  gap: 12px;
  justify-content: end;
  margin-top: auto;
  padding-top: 16px;
  border-top: 1px solid var(--rule);
}

.card-actions button,
.delete-page-dialog button {
  min-height: 48px;
  padding: 9px 14px;
  border: 1px solid var(--ink);
  border-radius: var(--radius-xs);
  color: var(--ink);
  background: transparent;
  cursor: pointer;
  white-space: nowrap;
}

.card-actions .save-action {
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

.delete-page-dialog {
  width: min(430px, calc(100% - 32px));
  padding: 24px;
  border: 1px solid var(--ink);
  color: var(--ink);
  background: var(--paper);
}

.delete-page-dialog::backdrop {
  background: color-mix(in srgb, var(--ink) 56%, transparent);
}

.delete-page-dialog h2 {
  margin: 0;
  font: 650 1.5rem var(--font-body);
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

@media (min-width: 960px) {
  .paper-meta-bar {
    grid-template-columns: minmax(0, 1.4fr) minmax(320px, 1fr);
    align-items: end;
  }

  .paper-details-popover {
    inset-inline-end: max(24px, calc((100vw - 960px) / 2 + 24px));
  }

  .card-page {
    min-height: 500px;
  }
}

@media (max-width: 479px) {
  .paper-name-row {
    grid-template-columns: 1fr;
    gap: 0;
  }

  .paper-details-popover {
    --details-top: 196px;
  }

  .paper-context-tools {
    justify-content: space-between;
    padding: 0;
  }

  .page-navigation button {
    grid-template-columns: 22px minmax(0, 1fr);
    padding-right: 4px;
  }

  .page-navigation {
    grid-auto-columns: calc((100% - 16px) / 3);
    column-gap: 8px;
  }

  .card-page {
    min-height: 532px;
  }

  .advanced-panel {
    grid-template-columns: 1fr;
  }

  .card-actions {
    grid-template-columns: 94px 104px minmax(0, 129px);
    width: 100%;
  }

  .card-actions button {
    padding-inline: 8px;
  }

  [lang="en"] .card-actions {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (orientation: portrait) {
  .card-page {
    min-height: 0;
  }

  .page-content-field {
    min-height: 0;
    flex: none;
  }

  .page-content-field textarea {
    min-height: 0;
    height: clamp(220px, 34dvh, 300px);
    flex: none;
    overflow-y: auto;
    resize: none;
  }

  .page-title-field input,
  .mode-toggle,
  .advanced-panel select,
  .page-content-field textarea {
    scroll-margin-bottom: calc(88px + env(safe-area-inset-bottom));
  }

  .card-actions {
    position: sticky;
    z-index: 2;
    bottom: 0;
    margin-top: 16px;
    padding-top: 12px;
    padding-bottom: calc(12px + env(safe-area-inset-bottom));
    background: var(--canvas);
  }
}

@media (forced-colors: active) {
  .paper-name-input:focus-visible,
  .paper-tags-input:focus-visible,
  .page-title-field input:focus-visible,
  .page-content-field textarea:focus-visible {
    outline-color: Highlight;
  }
}

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}
</style>

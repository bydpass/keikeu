<script setup>
import { computed, ref } from "vue";

const papers = ref([
  {
    id: "K-20260725-004",
    title: "场景节奏",
    path: "drafts/K-20260725-004.md",
    summary: "合成内容：记录场景目标、转折与待确认线索。",
    tags: "示例，节奏，待整理",
    highlights: [
      { name: "开场节拍", text: "用一个明确动作建立当前处境。" },
      { name: "信息转折", text: "中段只保留一条需要继续核对的线索。" },
      { name: "收束动作", text: "结尾回到角色可以立刻执行的下一步。" },
    ],
  },
  {
    id: "K-20260724-011",
    title: "角色动机",
    path: "notes/K-20260724-011.md",
    summary: "合成内容：区分角色说出的理由与真正驱动行动的理由。",
    tags: "示例，角色",
    highlights: [
      { name: "表层理由", text: "角色愿意公开表达的目标。" },
      { name: "行动压力", text: "迫使角色现在做出选择的条件。" },
    ],
  },
  {
    id: "K-20260723-002",
    title: "未命名 Paper",
    path: "inbox/K-20260723-002.md",
    summary: "合成内容：尚未分类的灵感片段。",
    tags: "",
    highlights: [{ name: "待整理", text: "确认它属于场景、角色还是结构问题。" }],
  },
]);

const query = ref("");
const selectedId = ref(papers.value[0].id);
const openMenu = ref(null);
const filteredPapers = computed(() => {
  const normalized = query.value.trim().toLocaleLowerCase();
  if (!normalized) {
    return papers.value;
  }
  return papers.value.filter((paper) =>
    `${paper.id} ${paper.title} ${paper.path}`.toLocaleLowerCase().includes(normalized),
  );
});
const selectedPaper = computed(
  () => papers.value.find((paper) => paper.id === selectedId.value) ?? papers.value[0],
);

function selectPaper(id) {
  selectedId.value = id;
  openMenu.value = null;
}

function moveHighlight(index, offset) {
  const destination = index + offset;
  if (destination < 0 || destination >= selectedPaper.value.highlights.length) {
    return;
  }
  const [highlight] = selectedPaper.value.highlights.splice(index, 1);
  selectedPaper.value.highlights.splice(destination, 0, highlight);
  openMenu.value = null;
}
</script>

<template>
  <div class="prototype-shell">
    <nav class="global-rail" aria-label="全局工作区">
      <a class="brand-mark" href="#paper-editor" aria-label="keikeu Paper">K</a>
      <div class="rail-nav" aria-label="Road v0.5 destinations">
        <a class="rail-item is-active" href="#paper-editor" aria-current="page">
          <span aria-hidden="true">P</span>
          <small>Paper</small>
        </a>
        <span class="rail-item is-preview" aria-disabled="true">
          <span aria-hidden="true">F</span>
          <small>Flash</small>
        </span>
        <span class="rail-item is-preview" aria-disabled="true">
          <span aria-hidden="true">L</span>
          <small>Library</small>
        </span>
      </div>
      <span class="local-mark" title="仅本地">LOCAL</span>
    </nav>

    <aside class="context-pane" aria-label="Paper 上下文">
      <header class="context-header">
        <p class="section-label">Road v0.5 · CP5</p>
        <h1>Paper 工作台</h1>
        <p class="prototype-notice">合成样张 · 不连接 Vault</p>
      </header>

      <label class="search-field">
        <span>筛选样张</span>
        <input v-model="query" type="search" placeholder="编号、名称或路径">
      </label>

      <section class="paper-index" aria-labelledby="paper-index-title">
        <div class="index-heading">
          <h2 id="paper-index-title">工作中的 Paper</h2>
          <span>{{ filteredPapers.length }}</span>
        </div>
        <ul class="paper-list">
          <li v-for="paper in filteredPapers" :key="paper.id">
            <button
              type="button"
              :class="{ 'is-selected': paper.id === selectedPaper.id }"
              @click="selectPaper(paper.id)"
            >
              <strong>{{ paper.title }}</strong>
              <span>{{ paper.id }}</span>
              <small>{{ paper.path }}</small>
            </button>
          </li>
        </ul>
        <p v-if="filteredPapers.length === 0" class="empty-copy">没有匹配的合成 Paper。</p>
      </section>

      <footer class="context-footer">
        <span>仅内存</span>
        <span>3 synthetic Papers</span>
      </footer>
    </aside>

    <main id="paper-editor" class="workspace">
      <header class="workspace-header">
        <div>
          <p class="section-label">编辑样张 / {{ selectedPaper.id }}</p>
          <h2>{{ selectedPaper.title }}</h2>
        </div>
        <button type="button" disabled title="CP5 样张不执行持久写入">样张不写入</button>
      </header>

      <div class="paper-layout">
        <form class="editor-sheet" @submit.prevent>
          <label class="field">
            <span>Paper 名称</span>
            <input v-model="selectedPaper.title" maxlength="120">
          </label>

          <label class="field summary-field">
            <span>Summary <b aria-hidden="true">*</b></span>
            <textarea v-model="selectedPaper.summary" rows="4" required />
            <small>先写清楚这张 Paper 要帮助你记住什么。</small>
          </label>

          <fieldset class="highlight-fieldset">
            <legend>
              <span>Highlights</span>
              <small>{{ selectedPaper.highlights.length }} 条</small>
            </legend>

            <ol class="highlight-list">
              <li
                v-for="(highlight, index) in selectedPaper.highlights"
                :key="highlight.name"
                class="highlight-row"
              >
                <span class="proof-number">{{ String(index + 1).padStart(2, "0") }}</span>
                <span class="drag-glyph" aria-hidden="true">⠿</span>
                <div>
                  <strong>{{ highlight.name }}</strong>
                  <p>{{ highlight.text }}</p>
                </div>
                <div class="row-actions">
                  <button
                    type="button"
                    :aria-expanded="openMenu === index"
                    :aria-label="`打开第 ${index + 1} 条 Highlight 排序菜单`"
                    @click="openMenu = openMenu === index ? null : index"
                  >
                    •••
                  </button>
                  <div v-if="openMenu === index" class="row-menu" role="menu">
                    <button
                      type="button"
                      role="menuitem"
                      :disabled="index === 0"
                      @click="moveHighlight(index, -1)"
                    >
                      上移
                    </button>
                    <button
                      type="button"
                      role="menuitem"
                      :disabled="index === selectedPaper.highlights.length - 1"
                      @click="moveHighlight(index, 1)"
                    >
                      下移
                    </button>
                  </div>
                </div>
              </li>
            </ol>
          </fieldset>

          <label class="field">
            <span>Tags</span>
            <input v-model="selectedPaper.tags" placeholder="以逗号分隔">
          </label>
        </form>

        <aside class="margin-note" aria-label="Paper 边注">
          <p class="section-label">Paper identity</p>
          <strong>{{ selectedPaper.id }}</strong>
          <code>{{ selectedPaper.path }}</code>
          <dl>
            <div>
              <dt>状态</dt>
              <dd>合成</dd>
            </div>
            <div>
              <dt>持久化</dt>
              <dd>关闭</dd>
            </div>
          </dl>
        </aside>
      </div>

      <footer class="workspace-status" aria-label="样张状态">
        <span><i class="status-dot" aria-hidden="true" /> 本地边界未调用</span>
        <span>Markdown canonical · Preview only</span>
      </footer>
    </main>
  </div>
</template>

<style scoped>
.prototype-shell {
  display: grid;
  grid-template-columns: 72px 260px minmax(0, 1fr);
  min-height: 100vh;
  color: var(--ink);
  background: var(--canvas);
}

button,
input,
textarea {
  font: inherit;
}

button {
  color: inherit;
}

.global-rail {
  display: flex;
  min-width: 0;
  flex-direction: column;
  align-items: center;
  padding: 18px 8px 14px;
  color: var(--paper);
  background: var(--rail);
}

.brand-mark {
  display: grid;
  width: 40px;
  height: 40px;
  border: 1px solid color-mix(in srgb, var(--paper) 60%, transparent);
  color: var(--paper);
  font: 600 1.35rem var(--font-display);
  place-items: center;
  text-decoration: none;
}

.rail-nav {
  display: grid;
  width: 100%;
  gap: 8px;
  margin-top: 34px;
}

.rail-item {
  display: grid;
  min-height: 58px;
  padding: 7px 2px;
  color: inherit;
  font-size: 1rem;
  place-items: center;
  text-align: center;
  text-decoration: none;
}

.rail-item small {
  color: var(--rail-muted);
  font-size: 0.62rem;
  letter-spacing: 0.04em;
}

.rail-item.is-active {
  border-left: 3px solid var(--signal);
  background: color-mix(in srgb, var(--paper) 8%, transparent);
}

.rail-item.is-preview {
  opacity: 0.48;
}

.local-mark {
  margin-top: auto;
  color: var(--rail-muted);
  font: 0.58rem var(--font-mono);
  letter-spacing: 0.14em;
  writing-mode: vertical-rl;
}

.context-pane {
  display: flex;
  min-width: 0;
  flex-direction: column;
  border-right: 1px solid var(--rule);
  background: var(--soft);
}

.context-header {
  padding: 28px 22px 18px;
  border-bottom: 1px solid var(--rule);
}

.section-label {
  margin: 0;
  color: var(--accent);
  font-size: 0.68rem;
  font-weight: 750;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.context-header h1 {
  margin: 7px 0 12px;
  font: 500 1.75rem/1.05 var(--font-display);
}

.prototype-notice {
  margin: 0;
  padding-left: 9px;
  border-left: 3px solid var(--signal);
  color: var(--muted);
  font-size: 0.76rem;
}

.search-field {
  display: grid;
  gap: 7px;
  padding: 18px 22px;
  border-bottom: 1px solid var(--rule);
  color: var(--muted);
  font-size: 0.72rem;
  font-weight: 700;
}

.search-field input,
.field input,
.field textarea {
  width: 100%;
  border: 1px solid var(--rule);
  border-radius: 0;
  color: var(--ink);
  background: var(--paper);
}

.search-field input {
  padding: 9px 10px;
  font-size: 0.82rem;
}

.paper-index {
  min-height: 0;
  flex: 1;
  padding: 20px 12px;
  overflow: auto;
}

.index-heading {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  padding: 0 10px 10px;
}

.index-heading h2 {
  margin: 0;
  font-size: 0.72rem;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.index-heading span {
  color: var(--muted);
  font: 0.72rem var(--font-mono);
}

.paper-list {
  display: grid;
  gap: 3px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.paper-list button {
  display: grid;
  width: 100%;
  gap: 4px;
  padding: 12px 10px;
  border: 0;
  border-left: 3px solid transparent;
  background: transparent;
  cursor: pointer;
  text-align: left;
}

.paper-list button:hover,
.paper-list button.is-selected {
  border-left-color: var(--signal);
  background: var(--paper);
}

.paper-list strong {
  font-size: 0.88rem;
}

.paper-list span,
.paper-list small {
  min-width: 0;
  overflow-wrap: anywhere;
  color: var(--muted);
  font: 0.68rem var(--font-mono);
}

.empty-copy {
  margin: 16px 10px;
  color: var(--muted);
  font-size: 0.82rem;
}

.context-footer,
.workspace-status {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: 8px;
  color: var(--muted);
  font: 0.65rem var(--font-mono);
}

.context-footer {
  padding: 12px 22px;
  border-top: 1px solid var(--rule);
}

.workspace {
  display: flex;
  min-width: 0;
  min-height: 100vh;
  flex-direction: column;
}

.workspace-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  padding: 26px 34px 20px;
  border-bottom: 1px solid var(--rule);
}

.workspace-header > div {
  min-width: 0;
}

.workspace-header h2 {
  margin: 5px 0 0;
  font: 500 clamp(1.9rem, 3vw, 2.8rem)/1 var(--font-display);
  overflow-wrap: anywhere;
}

.workspace-header button {
  padding: 9px 13px;
  border: 1px solid var(--rule);
  border-radius: var(--radius-xs);
  color: var(--muted);
  background: transparent;
}

.paper-layout {
  display: grid;
  grid-template-columns: minmax(420px, 760px) minmax(150px, 190px);
  justify-content: center;
  gap: 32px;
  padding: 32px 34px;
}

.editor-sheet {
  position: relative;
  display: grid;
  gap: 28px;
  padding: 36px 42px 44px 50px;
  border: 1px solid var(--rule);
  background: var(--paper);
}

.editor-sheet::before {
  position: absolute;
  top: 28px;
  bottom: 28px;
  left: 22px;
  width: 2px;
  background: var(--signal);
  content: "";
}

.field {
  display: grid;
  gap: 8px;
  color: var(--muted);
  font-size: 0.72rem;
  font-weight: 750;
  letter-spacing: 0.04em;
}

.field input,
.field textarea {
  padding: 11px 12px;
  line-height: 1.5;
  resize: vertical;
}

.field small {
  font-weight: 400;
  letter-spacing: 0;
}

.summary-field b {
  color: var(--signal);
}

.highlight-fieldset {
  min-width: 0;
  margin: 0;
  padding: 0;
  border: 0;
}

.highlight-fieldset legend {
  display: flex;
  width: 100%;
  align-items: baseline;
  justify-content: space-between;
  padding: 0 0 9px;
  border-bottom: 1px solid var(--ink);
  font-size: 0.76rem;
  font-weight: 750;
  letter-spacing: 0.04em;
}

.highlight-fieldset legend small {
  color: var(--muted);
  font: 0.68rem var(--font-mono);
}

.highlight-list {
  margin: 0;
  padding: 0;
  list-style: none;
}

.highlight-row {
  display: grid;
  grid-template-columns: 26px 20px minmax(0, 1fr) 36px;
  align-items: start;
  gap: 10px;
  padding: 15px 0;
  border-bottom: 1px solid var(--rule);
}

.proof-number {
  color: var(--signal);
  font: 0.67rem var(--font-mono);
}

.drag-glyph {
  color: var(--muted);
  line-height: 1;
}

.highlight-row strong {
  font: 600 0.85rem/1.3 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}

.highlight-row p {
  margin: 5px 0 0;
  color: var(--muted);
  font-size: 0.78rem;
  line-height: 1.5;
}

.row-actions {
  position: relative;
}

.row-actions > button {
  width: 34px;
  height: 30px;
  border: 0;
  background: transparent;
  cursor: pointer;
}

.row-menu {
  position: absolute;
  z-index: 2;
  top: 32px;
  right: 0;
  display: grid;
  min-width: 96px;
  padding: 4px;
  border: 1px solid var(--ink);
  background: var(--paper);
}

.row-menu button {
  padding: 7px 10px;
  border: 0;
  background: transparent;
  cursor: pointer;
  text-align: left;
}

.row-menu button:hover {
  background: var(--soft);
}

.row-menu button:disabled {
  cursor: not-allowed;
  opacity: 0.4;
}

.margin-note {
  align-self: start;
  padding: 16px 0 16px 15px;
  border-left: 2px solid var(--signal);
}

.margin-note > strong,
.margin-note code {
  display: block;
  margin-top: 10px;
  overflow-wrap: anywhere;
}

.margin-note > strong {
  font: 600 0.78rem var(--font-mono);
}

.margin-note code {
  color: var(--muted);
  font: 0.7rem/1.5 var(--font-mono);
}

.margin-note dl {
  display: grid;
  gap: 7px;
  margin: 22px 0 0;
}

.margin-note dl div {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  padding-top: 7px;
  border-top: 1px solid var(--rule);
}

.margin-note dt,
.margin-note dd {
  margin: 0;
  font-size: 0.68rem;
}

.margin-note dt {
  color: var(--muted);
}

.workspace-status {
  margin-top: auto;
  padding: 11px 34px;
  border-top: 1px solid var(--rule);
  background: var(--soft);
}

.status-dot {
  display: inline-block;
  width: 7px;
  height: 7px;
  margin-right: 5px;
  border: 1px solid var(--accent);
  border-radius: 50%;
}

:is(a, button, input, textarea):focus-visible {
  outline: 3px solid var(--accent);
  outline-offset: 2px;
}

@media (max-width: 1040px) {
  .prototype-shell {
    grid-template-columns: 64px 220px minmax(0, 1fr);
  }

  .paper-layout {
    grid-template-columns: minmax(0, 1fr);
  }

  .margin-note {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 10px 18px;
  }

  .margin-note dl {
    margin: 0;
  }
}

@media (max-width: 760px) {
  .prototype-shell {
    grid-template-columns: 1fr;
  }

  .global-rail {
    min-height: 64px;
    flex-direction: row;
    gap: 12px;
    padding: 10px 14px;
  }

  .rail-nav {
    display: flex;
    width: auto;
    gap: 4px;
    margin: 0;
  }

  .rail-item {
    min-width: 58px;
    min-height: 42px;
  }

  .rail-item.is-active {
    border-bottom: 3px solid var(--signal);
    border-left: 0;
  }

  .local-mark {
    margin: 0 0 0 auto;
    writing-mode: initial;
  }

  .context-pane {
    border-right: 0;
    border-bottom: 1px solid var(--rule);
  }

  .paper-index {
    max-height: 220px;
  }

  .workspace {
    min-height: auto;
  }

  .workspace-header,
  .paper-layout {
    padding-right: 18px;
    padding-left: 18px;
  }
}

@media (max-width: 520px) {
  .context-header,
  .search-field {
    padding-right: 16px;
    padding-left: 16px;
  }

  .workspace-header {
    align-items: flex-start;
    flex-direction: column;
  }

  .editor-sheet {
    padding: 28px 18px 34px 34px;
  }

  .editor-sheet::before {
    left: 14px;
  }

  .highlight-row {
    grid-template-columns: 22px 14px minmax(0, 1fr) 34px;
    gap: 6px;
  }

  .margin-note {
    grid-template-columns: 1fr;
  }
}

@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    scroll-behavior: auto !important;
  }
}
</style>

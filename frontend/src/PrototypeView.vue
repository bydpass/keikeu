<script setup>
import { computed, ref } from "vue";

import LibraryV4Projection from "./LibraryV4Projection.vue";
import PaperV4Workbench from "./PaperV4Workbench.vue";

const papers = ref([
  {
    path: "cache/夜车/K-20260802-001.md",
    code: "K-20260802-001",
    display_name: "夜车上的三句话",
    tags: ["夜车", "重逢,旧友"],
    pages: [
      { name: "为什么记住", content: "车门关闭前，对方只说了三句话。", type: "summary" },
      { name: "车窗", content: "灯光在玻璃上叠出两个人的影子。", type: "snapshot" },
      { name: "先别解释", content: "也许真正重要的是那段沉默。", type: "whisper" },
    ],
    created: "2026-08-02T09:00:00",
    updated: "2026-08-02T10:30:00",
  },
  {
    path: "cache/K-20260801-004.md",
    code: "K-20260801-004",
    display_name: "海边来信",
    tags: ["海风", "未寄出"],
    pages: [
      { name: "信封", content: "合成示例：信封边缘沾着细沙。", type: null },
      { name: "落款", content: "日期写了两遍，名字一次也没有。", type: "snapshot" },
    ],
    created: "2026-08-01T14:00:00",
    updated: "2026-08-01T15:10:00",
  },
  {
    path: "cache/K-20260731-009.md",
    code: "K-20260731-009",
    display_name: null,
    tags: [],
    pages: [{ name: null, content: "合成示例：一条尚未命名的灵感。", type: null }],
    created: "2026-07-31T18:00:00",
    updated: "2026-07-31T18:00:00",
  },
]);
const newPaperTemplate = {
  path: null,
  code: "K-SYNTHETIC-NEW",
  display_name: null,
  tags: [],
  pages: [{ name: null, content: "", type: null }],
  created: "2026-08-20T12:00:00",
  updated: "2026-08-20T12:00:00",
};

const destination = ref("paper");
const selectedPath = ref(papers.value[0].path);
const paperGeneration = ref(0);
const dirty = ref(false);
const toast = ref("");
const selectedPaper = computed(
  () => papers.value.find((paper) => paper.path === selectedPath.value) ?? newPaperTemplate,
);
const libraryEntries = computed(() =>
  papers.value.map((paper) => ({
    path: paper.path,
    code: paper.code,
    display_name: paper.display_name,
    folder: paper.path.split("/").length === 3 ? paper.path.split("/")[1] : null,
    tags: paper.tags,
    preview: paper.pages[0].content,
    page_count: paper.pages.length,
    page_names: paper.pages.map((page) => page.name).filter(Boolean),
    created: paper.created,
    updated: paper.updated,
  })),
);

function savePaper(editable) {
  const index = papers.value.findIndex((paper) => paper.code === editable.code);
  const saved = {
    ...(index === -1 ? newPaperTemplate : papers.value[index]),
    ...editable,
    path: index === -1 ? "cache/K-SYNTHETIC-NEW.md" : papers.value[index].path,
    updated: "2026-08-20T12:30:00",
  };
  if (index === -1) {
    papers.value.push(saved);
    selectedPath.value = saved.path;
    paperGeneration.value += 1;
  } else {
    papers.value[index] = saved;
  }
  toast.value = "合成保存完成；没有调用 Vault。";
}

function openPaper(path) {
  selectedPath.value = path;
  paperGeneration.value += 1;
  destination.value = "paper";
  toast.value = "";
}

function startNewPaper() {
  selectedPath.value = null;
  paperGeneration.value += 1;
  destination.value = "paper";
  toast.value = "新 Paper 只存在于合成内存。";
}
</script>

<template>
  <div class="prototype-v07-shell">
    <header class="prototype-v07-topbar">
      <strong class="prototype-v07-brand">keikeu</strong>
      <nav class="prototype-v07-daily" aria-label="Road v0.7 合成日常位置">
        <button
          type="button"
          :aria-current="destination === 'paper' ? 'page' : undefined"
          @click="destination = 'paper'"
        >
          Paper
        </button>
        <button
          type="button"
          :aria-current="destination === 'library' ? 'page' : undefined"
          @click="destination = 'library'"
        >
          Library
        </button>
      </nav>
      <div class="prototype-v07-actions" role="group" aria-label="工作区动作与环境">
        <button type="button" @click="startNewPaper">新 Paper</button>
        <button
          type="button"
          :aria-current="destination === 'vault' ? 'page' : undefined"
          @click="destination = 'vault'"
        >
          示例 Vault
        </button>
      </div>
    </header>

    <div class="prototype-v07-boundary">
      <strong>ROAD V0.7 · CP1 · DEVELOPMENT ONLY</strong>
      <span>合成样张 · 不连接 Vault · 无 bridge、文件 mutation 或持久配置</span>
    </div>

    <main class="prototype-v07-main">
      <section
        v-if="destination === 'paper'"
        class="prototype-v07-stage"
        aria-labelledby="prototype-paper-title"
      >
        <header class="prototype-v07-context">
          <div>
            <p>Paper</p>
            <h1 id="prototype-paper-title">
              {{ selectedPaper.display_name || "未命名 Paper" }}
            </h1>
          </div>
          <div class="prototype-v07-paper-state">
            <span>{{ dirty ? "草稿有未保存修改" : "草稿与合成基线一致" }}</span>
            <span v-if="toast" role="status">{{ toast }}</span>
          </div>
        </header>
        <PaperV4Workbench
          :key="paperGeneration"
          :paper="selectedPaper"
          state="ready"
          @dirty-change="dirty = $event"
          @save="savePaper"
        />
      </section>

      <section
        v-else-if="destination === 'library'"
        class="prototype-v07-stage prototype-v07-stage--library"
        aria-label="合成 Library 工作面"
      >
        <LibraryV4Projection
          :entries="libraryEntries"
          @open="openPaper"
        />
      </section>

      <section
        v-else-if="destination === 'vault'"
        class="prototype-v07-environment"
        aria-labelledby="prototype-vault-title"
      >
        <p class="prototype-v07-eyebrow">环境入口 · 不是第三个日常位置</p>
        <h1 id="prototype-vault-title">示例 Vault</h1>
        <p>当前环境状态正常。此视图只展示层级，不选择目录、不读取文件，也不保存配置。</p>
        <dl>
          <div><dt>状态</dt><dd>ready</dd></div>
          <div><dt>内容</dt><dd>{{ papers.length }} 份 synthetic Paper</dd></div>
          <div><dt>持久写入</dt><dd>无</dd></div>
        </dl>
        <details>
          <summary>显示合成路径说明</summary>
          <code>Home / Synthetic / keikeu-v07</code>
        </details>
        <div class="prototype-v07-environment-actions">
          <button type="button" @click="destination = 'paper'">返回 Paper</button>
          <button type="button" class="danger-action" @click="destination = 'blocked'">
            查看阻塞恢复样张
          </button>
        </div>
      </section>

      <section
        v-else
        class="prototype-v07-environment prototype-v07-blocked"
        aria-labelledby="prototype-blocked-title"
        aria-live="polite"
      >
        <p class="prototype-v07-eyebrow">本地环境已阻塞 · 合成状态</p>
        <h1 id="prototype-blocked-title">保存结果暂时无法确认</h1>
        <p>没有自动重发保存，也没有自动修改任何合成 Paper。当前工作面停止继续写入。</p>
        <dl>
          <div><dt>发生了什么</dt><dd>sidecar 在持久操作返回前断开。</dd></div>
          <div><dt>保留了什么</dt><dd>草稿与旧基线仍在内存中。</dd></div>
          <div><dt>安全动作</dt><dd>重启后只读对账；不 replay mutation。</dd></div>
        </dl>
        <button type="button" @click="destination = 'vault'">返回 Vault 环境</button>
      </section>
    </main>

    <footer class="prototype-v07-footer">
      <span>{{ papers.length }} synthetic Papers</span>
      <span>Vue 内存 DTO · production bundle 必须排除本页</span>
    </footer>
  </div>
</template>

<style scoped>
.prototype-v07-shell {
  --signal: #343432;
  --accent: #343432;
  display: grid;
  min-height: 100vh;
  grid-template-rows: auto auto minmax(0, 1fr) auto;
  color: var(--ink);
  background: var(--canvas);
}

button,
summary {
  font: inherit;
}

.prototype-v07-topbar {
  display: grid;
  grid-template-columns: auto auto minmax(20px, 1fr) auto;
  min-height: 56px;
  align-items: stretch;
  gap: 20px;
  padding: 0 26px;
  border-bottom: 1px solid var(--rule);
  background: var(--paper);
}

.prototype-v07-brand {
  align-self: center;
  font: 600 1.2rem var(--font-display);
}

.prototype-v07-daily,
.prototype-v07-actions {
  display: flex;
  align-items: stretch;
  gap: 4px;
}

.prototype-v07-actions {
  grid-column: 4;
}

.prototype-v07-topbar button {
  min-height: 44px;
  padding: 0 12px;
  border: 0;
  border-bottom: 3px solid transparent;
  color: var(--muted);
  background: transparent;
  cursor: pointer;
}

.prototype-v07-daily button[aria-current="page"],
.prototype-v07-actions button[aria-current="page"] {
  border-bottom-color: var(--ink);
  color: var(--ink);
  font-weight: 750;
}

.prototype-v07-boundary {
  display: flex;
  min-height: 34px;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  padding: 7px 26px;
  border-bottom: 1px solid var(--rule-soft);
  color: var(--meta);
  font: 0.66rem var(--font-mono);
}

.prototype-v07-boundary strong {
  color: var(--ink);
}

.prototype-v07-main {
  min-width: 0;
}

.prototype-v07-stage {
  min-width: 0;
  padding: 20px clamp(16px, 2.8vw, 34px) 36px;
}

.prototype-v07-context {
  display: flex;
  width: min(920px, 100%);
  align-items: end;
  justify-content: space-between;
  gap: 24px;
  margin: 0 auto 12px;
}

.prototype-v07-context p,
.prototype-v07-eyebrow {
  margin: 0;
  color: var(--meta);
  font-size: 0.68rem;
  font-weight: 750;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

.prototype-v07-context h1,
.prototype-v07-environment h1 {
  margin: 4px 0 0;
  font: 500 clamp(1.45rem, 2.6vw, 2.15rem) var(--font-display);
}

.prototype-v07-paper-state {
  display: grid;
  gap: 4px;
  color: var(--meta);
  font: 0.68rem var(--font-mono);
  text-align: right;
}

.prototype-v07-stage--library :deep(.library-v4-header) {
  padding-top: 0;
}

.prototype-v07-stage--library :deep(.library-v4-header h2) {
  font-size: clamp(1.45rem, 3vw, 2.15rem);
}

.prototype-v07-environment {
  width: min(760px, calc(100% - 32px));
  margin: 36px auto;
  padding: clamp(24px, 4vw, 42px);
  border: 1px solid var(--rule);
  border-top: 4px solid var(--ink);
  background: var(--paper);
}

.prototype-v07-environment > p:not(.prototype-v07-eyebrow) {
  max-width: 62ch;
  color: var(--muted);
}

.prototype-v07-environment dl {
  display: grid;
  gap: 8px;
  margin: 24px 0;
}

.prototype-v07-environment dl div {
  display: grid;
  grid-template-columns: 110px minmax(0, 1fr);
  gap: 14px;
  padding-top: 8px;
  border-top: 1px solid var(--rule-soft);
}

.prototype-v07-environment dt {
  color: var(--meta);
}

.prototype-v07-environment dd {
  margin: 0;
}

.prototype-v07-environment summary {
  cursor: pointer;
}

.prototype-v07-environment code {
  display: block;
  margin-top: 8px;
  overflow-wrap: anywhere;
}

.prototype-v07-environment button {
  min-height: 42px;
  padding: 8px 14px;
  border: 1px solid var(--ink);
  color: var(--ink);
  background: transparent;
  cursor: pointer;
}

.prototype-v07-environment-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 26px;
}

.prototype-v07-blocked {
  border-top-color: var(--danger);
}

.prototype-v07-blocked .prototype-v07-eyebrow {
  color: var(--danger);
}

.prototype-v07-blocked button {
  margin-top: 12px;
}

.prototype-v07-footer {
  display: flex;
  justify-content: space-between;
  gap: 14px;
  padding: 9px 26px;
  border-top: 1px solid var(--rule);
  color: var(--meta);
  font: 0.66rem var(--font-mono);
}

@media (max-width: 1000px) {
  .prototype-v07-stage--library :deep(.library-v4-layout) {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 760px) {
  .prototype-v07-topbar {
    grid-template-columns: auto 1fr;
    gap: 0 12px;
    padding: 8px 14px;
  }

  .prototype-v07-daily {
    justify-self: end;
  }

  .prototype-v07-actions {
    grid-column: 1 / -1;
    justify-content: flex-end;
  }

  .prototype-v07-boundary,
  .prototype-v07-context,
  .prototype-v07-footer {
    align-items: stretch;
    flex-direction: column;
  }

  .prototype-v07-paper-state {
    text-align: left;
  }

  .prototype-v07-environment dl div {
    grid-template-columns: 1fr;
    gap: 3px;
  }
}
</style>

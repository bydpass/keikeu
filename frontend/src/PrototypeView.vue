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

const destination = ref("paper");
const selectedPath = ref(papers.value[0].path);
const paperState = ref("ready");
const dirty = ref(false);
const toast = ref("");
const selectedPaper = computed(
  () => papers.value.find((paper) => paper.path === selectedPath.value) ?? papers.value[0],
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
  papers.value[index] = {
    ...papers.value[index],
    ...editable,
    updated: "2026-08-02T12:00:00",
  };
  toast.value = "合成保存完成；没有调用 Vault。";
}

function openPaper(path) {
  selectedPath.value = path;
  destination.value = "paper";
  paperState.value = "ready";
}
</script>

<template>
  <div class="prototype-v4-shell">
    <nav class="prototype-v4-rail" aria-label="Road v0.6 合成工作区">
      <span class="prototype-v4-brand" aria-label="keikeu">K</span>
      <button
        type="button"
        :class="{ active: destination === 'paper' }"
        @click="destination = 'paper'"
      >
        Paper
      </button>
      <button
        type="button"
        :class="{ active: destination === 'library' }"
        @click="destination = 'library'"
      >
        Library
      </button>
      <span class="prototype-v4-local">LOCAL</span>
    </nav>

    <main class="prototype-v4-main">
      <header class="prototype-v4-header">
        <div>
          <p>ROAD V0.6 · CP3 · DEVELOPMENT ONLY</p>
          <h1>{{ destination === "paper" ? "Paper 就是最后留下的卡页" : "一份 Paper，一个资产" }}</h1>
        </div>
        <div class="prototype-v4-notice">
          <strong>合成样张 · 不连接 Vault</strong>
          <span>无 bridge、无路径 mutation、无持久配置</span>
        </div>
      </header>

      <section v-if="destination === 'paper'" class="prototype-v4-stage">
        <div class="prototype-toolbar" aria-label="合成恢复状态">
          <label>
            <span>恢复状态样张</span>
            <select v-model="paperState">
              <option value="ready">正常</option>
              <option value="stale">stale</option>
              <option value="repair_required">repair</option>
              <option value="index_degraded">index degraded</option>
              <option value="commit_unknown">commit unknown</option>
            </select>
          </label>
          <span>{{ dirty ? "DIRTY" : "CLEAN" }}</span>
          <span v-if="toast" role="status">{{ toast }}</span>
        </div>
        <PaperV4Workbench
          :paper="selectedPaper"
          :state="paperState"
          @dirty-change="dirty = $event"
          @save="savePaper"
        />
      </section>

      <section v-else class="prototype-v4-stage">
        <LibraryV4Projection
          :entries="libraryEntries"
          :index-state="paperState === 'index_degraded' ? 'degraded' : 'current'"
          :errors="paperState === 'repair_required'
            ? [{ path: 'cache/synthetic-broken.md', reason: 'page marker 缺失' }]
            : []"
          @open="openPaper"
          @rebuild-index="paperState = 'ready'"
        />
      </section>

      <footer class="prototype-v4-footer">
        <span>3 synthetic Papers</span>
        <span>Vue 内存 DTO · protocol 未调用</span>
      </footer>
    </main>
  </div>
</template>

<style scoped>
.prototype-v4-shell {
  display: grid;
  grid-template-columns: 92px minmax(0, 1fr);
  min-height: 100vh;
  color: var(--ink);
  background: var(--canvas);
}

button,
select {
  font: inherit;
}

.prototype-v4-rail {
  position: sticky;
  top: 0;
  display: flex;
  height: 100vh;
  flex-direction: column;
  align-items: stretch;
  gap: 8px;
  padding: 18px 10px;
  color: var(--paper);
  background: var(--rail);
}

.prototype-v4-brand {
  display: grid;
  width: 44px;
  height: 44px;
  align-self: center;
  margin-bottom: 26px;
  border: 1px solid var(--paper);
  font: 600 22px var(--font-display);
  place-items: center;
}

.prototype-v4-rail button {
  min-height: 52px;
  padding: 8px 4px;
  border: 0;
  border-left: 3px solid transparent;
  color: var(--rail-muted);
  background: transparent;
  cursor: pointer;
  font-size: 0.72rem;
}

.prototype-v4-rail button.active {
  border-left-color: var(--paper);
  color: var(--paper);
  background: var(--rail-active);
}

.prototype-v4-local {
  margin-top: auto;
  color: var(--rail-muted);
  font: 0.58rem var(--font-mono);
  letter-spacing: 0.15em;
  text-align: center;
}

.prototype-v4-main {
  display: flex;
  min-width: 0;
  min-height: 100vh;
  flex-direction: column;
}

.prototype-v4-header {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 28px;
  padding: 24px 34px 18px;
  border-bottom: 1px solid var(--rule);
}

.prototype-v4-header p {
  margin: 0;
  color: var(--signal);
  font-size: 0.66rem;
  font-weight: 750;
  letter-spacing: 0.12em;
}

.prototype-v4-header h1 {
  margin: 7px 0 0;
  font: 500 clamp(1.8rem, 3vw, 2.8rem) var(--font-display);
}

.prototype-v4-notice {
  display: grid;
  gap: 3px;
  padding-left: 14px;
  border-left: 4px solid var(--signal);
  font-size: 0.74rem;
}

.prototype-v4-notice span {
  color: var(--meta);
}

.prototype-v4-stage {
  flex: 1;
  padding: 28px 34px 36px;
}

.prototype-toolbar {
  display: flex;
  width: min(920px, 100%);
  min-height: 42px;
  align-items: center;
  gap: 16px;
  margin: 0 auto 12px;
  color: var(--meta);
  font: 0.68rem var(--font-mono);
}

.prototype-toolbar label {
  display: flex;
  align-items: center;
  gap: 8px;
}

.prototype-toolbar select {
  min-height: 34px;
  border: 1px solid var(--rule);
  background: var(--paper);
}

.prototype-v4-footer {
  display: flex;
  justify-content: space-between;
  gap: 14px;
  padding: 10px 34px;
  border-top: 1px solid var(--rule);
  color: var(--meta);
  font: 0.66rem var(--font-mono);
}

@media (max-width: 720px) {
  .prototype-v4-shell {
    grid-template-columns: 1fr;
  }

  .prototype-v4-rail {
    position: static;
    height: auto;
    flex-direction: row;
    align-items: center;
  }

  .prototype-v4-brand {
    margin: 0 12px 0 0;
  }

  .prototype-v4-rail button {
    min-width: 72px;
    border-bottom: 3px solid transparent;
    border-left: 0;
  }

  .prototype-v4-rail button.active {
    border-bottom-color: var(--paper);
  }

  .prototype-v4-local {
    margin: 0 0 0 auto;
  }

  .prototype-v4-header {
    align-items: stretch;
    flex-direction: column;
  }

  .prototype-v4-stage {
    padding-inline: 16px;
  }
}
</style>

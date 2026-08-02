<script setup>
import { computed, ref, watch } from "vue";

const props = defineProps({
  entries: { type: Array, required: true },
  errors: { type: Array, default: () => [] },
  indexState: { type: String, default: "current" },
  query: { type: String, default: "" },
});
const emit = defineEmits([
  "open",
  "rebuild-index",
  "reveal-error",
  "search",
  "select",
]);

const query = ref(props.query);
const selectedPath = ref(props.entries[0]?.path ?? null);
const normalizedQuery = computed(() => query.value.trim().toLocaleLowerCase());
const filteredEntries = computed(() => {
  if (!normalizedQuery.value) {
    return props.entries;
  }
  return props.entries.filter((entry) =>
    [
      entry.display_name,
      entry.code,
      entry.folder,
      entry.preview,
      ...(entry.tags ?? []),
      ...(entry.page_names ?? []),
    ]
      .filter(Boolean)
      .join("\0")
      .toLocaleLowerCase()
      .includes(normalizedQuery.value),
  );
});
const selected = computed(
  () => filteredEntries.value.find((entry) => entry.path === selectedPath.value)
    ?? filteredEntries.value[0]
    ?? null,
);

watch(
  () => props.entries,
  (entries) => {
    if (!entries.some((entry) => entry.path === selectedPath.value)) {
      selectedPath.value = entries[0]?.path ?? null;
    }
  },
);
watch(() => props.query, (value) => { query.value = value; });
watch(selected, (value) => emit("select", value?.path ?? null), { immediate: true });

function label(entry) {
  return entry.display_name || entry.code;
}
</script>

<template>
  <section class="library-v4-projection">
    <header class="library-v4-header">
      <div>
        <p>LOCAL LIBRARY · PAPER V4</p>
        <h2>从 Paper 找回灵感</h2>
      </div>
      <label>
        <span>搜索名称、Tags、所有页</span>
        <input
          v-model="query"
          type="search"
          placeholder="搜索所有卡页"
          @input="emit('search', query)"
        >
      </label>
    </header>

    <p v-if="indexState === 'degraded'" class="index-warning" role="status">
      Index 可能过期；Paper 内容仍可用。
      <button type="button" @click="emit('rebuild-index')">显式重建 Index</button>
    </p>

    <div class="library-v4-layout">
      <section aria-labelledby="library-results-title">
        <div class="library-count">
          <h3 id="library-results-title">Paper</h3>
          <span>{{ filteredEntries.length }} / {{ entries.length }}</span>
        </div>
        <ul class="library-v4-list">
          <li v-for="entry in filteredEntries" :key="entry.path">
            <button
              type="button"
              :class="{ selected: entry.path === selected?.path }"
              @click="selectedPath = entry.path"
            >
              <strong>{{ label(entry) }}</strong>
              <span>{{ entry.code }} · {{ entry.page_count }} 页</span>
              <small>{{ entry.folder || "未归档" }}</small>
              <p>{{ entry.preview }}</p>
            </button>
          </li>
        </ul>
        <p v-if="filteredEntries.length === 0" class="library-empty">没有匹配的 Paper。</p>
      </section>

      <aside v-if="selected" class="library-v4-detail" aria-label="Paper 详情">
        <p>SELECTED PAPER</p>
        <h3>{{ label(selected) }}</h3>
        <code>{{ selected.code }}</code>
        <dl>
          <div>
            <dt>文件夹</dt>
            <dd>{{ selected.folder || "未归档" }}</dd>
          </div>
          <div>
            <dt>页数</dt>
            <dd>{{ selected.page_count }}</dd>
          </div>
          <div>
            <dt>Tags</dt>
            <dd>{{ selected.tags.length ? selected.tags.join(" · ") : "无" }}</dd>
          </div>
          <div>
            <dt>页标题</dt>
            <dd>{{ selected.page_names.length ? selected.page_names.join(" · ") : "无" }}</dd>
          </div>
          <div>
            <dt>更新时间</dt>
            <dd>{{ selected.updated }}</dd>
          </div>
        </dl>
        <button type="button" class="open-paper" @click="emit('open', selected.path)">
          打开整份 Paper
        </button>
        <small>始终从第一页打开；不 deep-link 到单页。</small>
      </aside>
    </div>

    <details v-if="errors.length" class="library-errors">
      <summary>{{ errors.length }} 个 Paper 需要人工修复</summary>
      <ul>
        <li v-for="error in errors" :key="error.path">
          <code>{{ error.path }}</code>：{{ error.reason }}
          <button type="button" @click="emit('reveal-error', error.path)">
            在 Finder 中显示
          </button>
        </li>
      </ul>
    </details>
  </section>
</template>

<style scoped>
.library-v4-projection {
  width: min(1060px, 100%);
  margin: 0 auto;
}

button,
input {
  font: inherit;
}

.library-v4-header {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 28px;
  padding: 22px 0;
  border-bottom: 2px solid var(--ink);
}

.library-v4-header p,
.library-v4-detail > p {
  margin: 0;
  color: var(--signal);
  font-size: 0.66rem;
  font-weight: 750;
  letter-spacing: 0.12em;
}

.library-v4-header h2 {
  margin: 6px 0 0;
  font: 500 clamp(1.8rem, 4vw, 3rem) var(--font-display);
}

.library-v4-header label {
  display: grid;
  width: min(360px, 100%);
  gap: 6px;
  color: var(--muted);
  font-size: 0.72rem;
  font-weight: 700;
}

.library-v4-header input {
  min-height: 42px;
  padding: 9px 12px;
  border: 1px solid var(--rule);
  color: var(--ink);
  background: var(--paper);
}

.index-warning {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  margin: 16px 0 0;
  padding: 10px 14px;
  border-left: 4px solid var(--danger);
  background: var(--danger-soft);
  font-size: 0.8rem;
}

.index-warning button {
  padding: 6px 10px;
  border: 1px solid var(--danger);
  color: var(--danger);
  background: transparent;
  cursor: pointer;
}

.library-v4-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(240px, 310px);
  gap: 34px;
  padding: 26px 0;
}

.library-count {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  padding-bottom: 9px;
  border-bottom: 1px solid var(--rule);
}

.library-count h3 {
  margin: 0;
  font-size: 0.78rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.library-count span {
  color: var(--meta);
  font: 0.7rem var(--font-mono);
}

.library-v4-list {
  display: grid;
  gap: 5px;
  margin: 0;
  padding: 10px 0 0;
  list-style: none;
}

.library-v4-list button {
  display: grid;
  width: 100%;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 4px 18px;
  padding: 16px 14px;
  border: 1px solid transparent;
  border-left: 4px solid transparent;
  color: var(--ink);
  background: transparent;
  cursor: pointer;
  text-align: left;
}

.library-v4-list button:hover,
.library-v4-list button.selected {
  border-color: var(--rule);
  border-left-color: var(--signal);
  background: var(--paper);
}

.library-v4-list strong {
  font-size: 0.95rem;
}

.library-v4-list span,
.library-v4-list small {
  color: var(--meta);
  font: 0.68rem var(--font-mono);
}

.library-v4-list small {
  grid-column: 1;
}

.library-v4-list p {
  display: -webkit-box;
  grid-column: 1 / -1;
  margin: 7px 0 0;
  overflow: hidden;
  color: var(--muted);
  font-size: 0.8rem;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.library-v4-detail {
  align-self: start;
  padding: 20px;
  border: 1px solid var(--rule);
  border-top: 4px solid var(--signal);
  background: var(--paper);
}

.library-v4-detail h3 {
  margin: 8px 0 3px;
  font: 500 1.5rem var(--font-display);
}

.library-v4-detail code {
  color: var(--meta);
  font-size: 0.7rem;
}

.library-v4-detail dl {
  display: grid;
  gap: 8px;
  margin: 22px 0;
}

.library-v4-detail dl div {
  display: grid;
  grid-template-columns: 72px minmax(0, 1fr);
  gap: 10px;
  padding-top: 8px;
  border-top: 1px solid var(--rule-soft);
}

.library-v4-detail dt {
  color: var(--meta);
  font-size: 0.7rem;
}

.library-v4-detail dd {
  margin: 0;
  overflow-wrap: anywhere;
  font-size: 0.74rem;
}

.open-paper {
  width: 100%;
  min-height: 44px;
  border: 1px solid var(--signal);
  color: var(--paper);
  background: var(--signal);
  cursor: pointer;
}

.library-v4-detail > small {
  display: block;
  margin-top: 8px;
  color: var(--meta);
  font-size: 0.66rem;
}

.library-errors {
  margin-bottom: 24px;
  padding: 12px 14px;
  border: 1px solid var(--danger);
  background: var(--danger-soft);
  font-size: 0.78rem;
}

.library-errors summary {
  cursor: pointer;
  font-weight: 700;
}

.library-errors code {
  font-size: 0.7rem;
}

.library-errors button {
  min-height: 36px;
  margin-left: 8px;
  border: 1px solid var(--danger);
  color: var(--danger);
  background: transparent;
  cursor: pointer;
}

.library-empty {
  padding: 28px 14px;
  color: var(--meta);
}

@media (max-width: 760px) {
  .library-v4-header {
    align-items: stretch;
    flex-direction: column;
  }

  .library-v4-header label {
    width: 100%;
  }

  .library-v4-layout {
    grid-template-columns: 1fr;
  }
}
</style>

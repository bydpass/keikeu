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

const emit = defineEmits(["runtime-blocked", "open-paper", "open-library"]);

const deck = ref(null);
const index = ref(0);
const selectedPath = ref(props.initialPath ?? "");
const jumpPage = ref("1");
const showSummary = ref(false);
const busy = ref(false);
const notice = ref("");
const error = ref(null);

const currentCard = computed(() => deck.value?.cards?.[index.value] ?? null);
const isHighlight = computed(() => index.value > 0);

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

function handleError(rawError, fallback) {
  const normalized = normalizeError(rawError);
  const visible = {
    ...normalized,
    message: `${fallback}：${normalized.message}`,
  };
  if (
    normalized.layer === "tauri_host" ||
    ["protocol_mismatch", "sidecar_unavailable"].includes(normalized.code)
  ) {
    emit("runtime-blocked", visible);
    return;
  }
  error.value = visible;
}

function applyDeck(nextDeck) {
  if (
    !nextDeck ||
    typeof nextDeck.path !== "string" ||
    !Array.isArray(nextDeck.cards) ||
    nextDeck.cards.length === 0 ||
    !Array.isArray(nextDeck.options)
  ) {
    throw {
      code: "operation_failed",
      layer: "vue_ui",
      message: "Flashcard 数据不完整。",
      recovery: "return_to_paper",
    };
  }
  deck.value = nextDeck;
  selectedPath.value = nextDeck.path;
  index.value = 0;
  jumpPage.value = "1";
  showSummary.value = false;
  notice.value = "";
  error.value = null;
}

async function loadDeck(path) {
  if (busy.value) {
    return;
  }
  const previousPath = deck.value?.path ?? "";
  busy.value = true;
  notice.value = "";
  try {
    applyDeck(await bridgeRequest("flashcard.open", { path: path || null }));
  } catch (rawError) {
    selectedPath.value = previousPath;
    handleError(rawError, "无法打开 Flashcard");
  } finally {
    busy.value = false;
  }
}

function selectCard(nextIndex) {
  if (!deck.value || nextIndex < 0 || nextIndex >= deck.value.cards.length) {
    return;
  }
  index.value = nextIndex;
  jumpPage.value = String(nextIndex + 1);
  showSummary.value = false;
  notice.value = "";
}

function move(offset) {
  if (!deck.value) {
    return;
  }
  const nextIndex = index.value + offset;
  if (nextIndex < 0) {
    notice.value = "已经是第一张。";
    return;
  }
  if (nextIndex >= deck.value.cards.length) {
    notice.value = "已经是最后一张。";
    return;
  }
  selectCard(nextIndex);
}

function jump() {
  const raw = String(jumpPage.value).trim();
  const total = deck.value?.cards?.length ?? 0;
  if (!/^\d+$/.test(raw) || Number(raw) < 1 || Number(raw) > total) {
    notice.value = `页码范围是 1..${total}。`;
    return;
  }
  selectCard(Number(raw) - 1);
}

function switchPaper() {
  loadDeck(selectedPath.value);
}

function returnToPaper() {
  emit("open-paper", deck.value?.path ?? props.initialPath);
}

function openLibrary() {
  emit("open-library");
}

function onWindowKeydown(event) {
  if (["INPUT", "TEXTAREA", "SELECT"].includes(event.target?.tagName)) {
    return;
  }
  if (event.key === "ArrowLeft") {
    event.preventDefault();
    move(-1);
  } else if (event.key === "ArrowRight") {
    event.preventDefault();
    move(1);
  }
}

onMounted(() => {
  window.addEventListener("keydown", onWindowKeydown);
  loadDeck(props.initialPath);
});

onUnmounted(() => window.removeEventListener("keydown", onWindowKeydown));
</script>

<template>
  <main v-if="busy && !deck" class="flashcard-gate" aria-live="polite">
    <section>
      <p class="flashcard-eyebrow">Road v0.4 · Flashcard</p>
      <h1>正在打开 Flashcard</h1>
      <p>从 Python Core 读取 Summary-first 投影。</p>
    </section>
  </main>

  <main v-else-if="!deck" class="flashcard-gate" aria-live="assertive">
    <section class="flashcard-gate-error">
      <p class="flashcard-eyebrow">Flashcard · 只读</p>
      <h1>尚未打开 Paper</h1>
      <p>{{ error?.message ?? "Vault 中没有可读取的 Paper。" }}</p>
      <button type="button" @click="returnToPaper">返回 Paper</button>
    </section>
  </main>

  <div v-else class="flashcard-shell">
    <nav class="flashcard-rail" aria-label="全局工作区">
      <span class="flashcard-brand" aria-label="keikeu">K</span>
      <button
        class="flashcard-destination"
        type="button"
        aria-label="返回 Paper"
        @click="returnToPaper"
      >P<small>Paper</small></button>
      <span class="flashcard-destination is-active" aria-current="page">
        F<small>Flash</small>
      </span>
      <button
        class="flashcard-destination"
        type="button"
        aria-label="打开 Library"
        @click="openLibrary"
      >L<small>Library</small></button>
      <span class="flashcard-local">LOCAL</span>
    </nav>

    <aside class="flashcard-context" aria-labelledby="flashcard-list-title">
      <header>
        <p class="flashcard-eyebrow">Road v0.4 · Flashcard</p>
        <h1 id="flashcard-list-title">Flashcard</h1>
        <p>只读投影 · {{ runtime.core_version }}</p>
      </header>

      <label class="flashcard-selector">
        <span>Paper</span>
        <select v-model="selectedPath" :disabled="busy" @change="switchPaper">
          <option
            v-for="option in deck.options"
            :key="option.path"
            :value="option.path"
          >{{ option.label }}</option>
        </select>
      </label>

      <nav aria-label="Flashcard 列表">
        <h2>卡片 <span>{{ deck.cards.length }}</span></h2>
        <ol class="flashcard-list">
          <li v-for="(card, cardIndex) in deck.cards" :key="cardIndex">
            <button
              type="button"
              :class="{ selected: cardIndex === index }"
              :aria-current="cardIndex === index ? 'page' : undefined"
              @click="selectCard(cardIndex)"
            >
              <span>{{ String(cardIndex + 1).padStart(2, "0") }}</span>
              <strong>{{ card.title }}</strong>
            </button>
          </li>
        </ol>
      </nav>
    </aside>

    <main class="flashcard-workspace">
      <header class="flashcard-workspace-header">
        <div>
          <p class="flashcard-eyebrow">Summary-first · page {{ index + 1 }}</p>
          <h2>{{ deck.paper_label }}</h2>
        </div>
        <span>{{ index + 1 }} / {{ deck.cards.length }}</span>
      </header>

      <div class="flashcard-stage">
        <article class="flashcard-reader" aria-live="polite">
          <p class="flashcard-kind">{{ currentCard.title }}</p>
          <p class="flashcard-content">{{ currentCard.content }}</p>

          <section v-if="isHighlight" class="summary-tools">
            <button type="button" @click="showSummary = !showSummary">
              {{ showSummary ? "收起当前 Summary" : "查看当前 Summary" }}
            </button>
            <aside v-if="showSummary" class="summary-context">
              <h3>当前 Summary（仅供对照）</h3>
              <p>{{ deck.cards[0].content }}</p>
            </aside>
          </section>

          <p v-if="error" class="flashcard-error" aria-live="assertive">
            {{ error.message }}
          </p>
          <p v-if="notice" class="flashcard-notice" aria-live="polite">{{ notice }}</p>

          <div class="flashcard-controls">
            <button type="button" :disabled="busy" @click="move(-1)">上一张</button>
            <button class="primary-action" type="button" :disabled="busy" @click="move(1)">
              下一张
            </button>
            <form @submit.prevent="jump">
              <label for="flashcard-jump-page">第</label>
              <input
                id="flashcard-jump-page"
                v-model="jumpPage"
                type="number"
                min="1"
                :max="deck.cards.length"
                inputmode="numeric"
              >
              <span>页</span>
              <button type="submit">跳转</button>
            </form>
            <button type="button" @click="returnToPaper">返回 Paper</button>
          </div>
        </article>

        <aside class="flashcard-margin" aria-label="Flashcard 边注">
          <p class="flashcard-eyebrow">Paper identity</p>
          <strong>{{ deck.paper_label }}</strong>
          <code>{{ deck.path }}</code>
          <p>位置仅保存在当前 Vue 内存；重新打开从第 1 页开始。</p>
        </aside>
      </div>
    </main>
  </div>
</template>

<style scoped>
.flashcard-shell {
  display: grid;
  grid-template-columns: 72px 260px minmax(0, 1fr);
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

.flashcard-eyebrow {
  margin: 0;
  color: var(--muted, #646b68);
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.flashcard-gate {
  display: grid;
  min-height: 100vh;
  padding: 32px;
  place-items: center;
  background: var(--canvas);
}

.flashcard-gate > section {
  width: min(680px, 100%);
  padding: 40px;
  border: 1px solid var(--rule);
  border-top: 4px solid var(--accent);
  background: var(--paper);
}

.flashcard-gate h1 {
  margin: 10px 0 16px;
  font-family: Georgia, "Times New Roman", serif;
  font-size: clamp(2rem, 6vw, 3.5rem);
  font-weight: 500;
  line-height: 1.08;
}

.flashcard-gate button {
  margin-top: 20px;
  color: var(--paper);
  background: var(--accent);
}

.flashcard-gate-error {
  border-top-color: var(--danger) !important;
}

.flashcard-rail {
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
  background: var(--ink);
}

.flashcard-brand {
  display: grid;
  width: 38px;
  height: 38px;
  border: 1px solid var(--paper);
  place-items: center;
  font-family: Georgia, "Times New Roman", serif;
  font-size: 1.4rem;
}

.flashcard-destination {
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

.flashcard-destination small {
  font-size: 0.58rem;
  font-weight: 500;
}

.flashcard-destination.is-active {
  border-left: 3px solid var(--signal);
  color: var(--paper);
  background: var(--rail-active);
}

.flashcard-local {
  margin-top: auto;
  font: 0.58rem ui-monospace, SFMono-Regular, Menlo, monospace;
  letter-spacing: 0.12em;
}

.flashcard-context {
  grid-column: 2;
  min-width: 0;
  padding: 28px 20px;
  border-right: 1px solid var(--rule);
  background: var(--soft);
}

.flashcard-context h1,
.flashcard-workspace h2 {
  margin: 8px 0;
  font-family: Georgia, "Times New Roman", serif;
  font-weight: 500;
}

.flashcard-context header > p:last-child {
  color: var(--muted);
  font-size: 0.78rem;
}

.flashcard-selector {
  display: grid;
  gap: 7px;
  margin: 20px 0 28px;
  font-size: 0.82rem;
  font-weight: 650;
}

.flashcard-selector select,
.flashcard-controls input {
  min-width: 0;
  border: 1px solid var(--rule);
  padding: 10px 11px;
  color: var(--ink);
  background: var(--field);
}

.flashcard-context h2 {
  display: flex;
  justify-content: space-between;
  margin: 0 0 10px;
  font-size: 0.78rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.flashcard-list {
  display: grid;
  gap: 6px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.flashcard-list button {
  display: grid;
  width: 100%;
  grid-template-columns: 32px minmax(0, 1fr);
  gap: 8px;
  border-color: transparent;
  text-align: left;
  background: transparent;
}

.flashcard-list button.selected {
  border-color: var(--rule);
  border-left: 3px solid var(--signal);
  background: var(--paper);
}

.flashcard-list span {
  color: var(--muted);
  font: 0.7rem ui-monospace, SFMono-Regular, Menlo, monospace;
}

.flashcard-workspace {
  grid-column: 3;
  min-width: 0;
  padding: 30px clamp(24px, 4vw, 56px) 64px;
}

.flashcard-workspace-header {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 20px;
  padding-bottom: 18px;
  border-bottom: 1px solid var(--rule);
}

.flashcard-workspace-header h2 {
  font-size: clamp(2rem, 4vw, 3.2rem);
}

.flashcard-workspace-header > span {
  color: var(--accent);
  font: 0.78rem ui-monospace, SFMono-Regular, Menlo, monospace;
}

.flashcard-stage {
  display: grid;
  grid-template-columns: minmax(0, 720px) minmax(160px, 220px);
  gap: clamp(24px, 4vw, 52px);
  margin-top: 28px;
}

.flashcard-reader {
  min-height: 420px;
  padding: 32px;
  border: 1px solid var(--rule);
  border-top: 3px solid var(--signal);
  background: var(--paper);
}

.flashcard-kind {
  margin: 0;
  color: var(--muted);
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.flashcard-content {
  min-height: 180px;
  margin: 28px 0;
  font-family: Georgia, "Times New Roman", serif;
  font-size: clamp(1.5rem, 3vw, 2.25rem);
  line-height: 1.45;
  overflow-wrap: anywhere;
  white-space: pre-wrap;
}

.summary-tools {
  margin: 24px 0;
}

.summary-context {
  margin-top: 12px;
  padding: 16px;
  border-left: 3px solid var(--accent);
  background: var(--soft);
}

.summary-context h3,
.summary-context p {
  margin: 0;
}

.summary-context p {
  margin-top: 8px;
  line-height: 1.55;
  white-space: pre-wrap;
}

.flashcard-error,
.flashcard-notice {
  margin: 16px 0;
}

.flashcard-error {
  color: var(--danger);
}

.flashcard-notice {
  color: var(--muted);
}

.flashcard-controls,
.flashcard-controls form {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

.flashcard-controls {
  margin-top: 28px;
}

.flashcard-controls input {
  width: 70px;
  padding: 8px;
}

.primary-action {
  color: var(--paper);
  background: var(--accent);
}

.flashcard-margin {
  align-self: start;
  padding-left: 16px;
  border-left: 2px solid var(--signal);
}

.flashcard-margin > strong,
.flashcard-margin > code {
  display: block;
  margin-top: 10px;
  overflow-wrap: anywhere;
}

.flashcard-margin > code,
.flashcard-margin > p:last-child {
  color: var(--muted);
  font: 0.72rem ui-monospace, SFMono-Regular, Menlo, monospace;
}

@media (max-width: 1100px) {
  .flashcard-stage {
    grid-template-columns: 1fr;
  }

  .flashcard-margin {
    order: -1;
  }
}

@media (max-width: 760px) {
  .flashcard-shell {
    grid-template-columns: 56px minmax(0, 1fr);
  }

  .flashcard-rail {
    grid-row: 1 / span 2;
    width: 56px;
  }

  .flashcard-context {
    border-right: 0;
    border-bottom: 1px solid var(--rule);
  }

  .flashcard-workspace {
    grid-column: 2;
    padding: 24px 18px 48px;
  }
}

@media (max-width: 520px) {
  .flashcard-shell {
    display: block;
  }

  .flashcard-rail {
    position: static;
    width: auto;
    height: auto;
    flex-direction: row;
    justify-content: space-between;
    overflow-y: visible;
  }

  .flashcard-local {
    margin: 0;
  }

  .flashcard-context {
    padding: 22px 16px;
  }

  .flashcard-workspace-header {
    align-items: start;
    flex-direction: column;
  }

  .flashcard-reader {
    min-height: 0;
    padding: 24px 18px;
  }

  .flashcard-gate {
    padding: 16px;
  }

  .flashcard-gate > section {
    padding: 24px;
  }
}
</style>

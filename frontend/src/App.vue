<script setup>
import { defineAsyncComponent, onMounted, onUnmounted, ref } from "vue";

import { getRuntimeStatus, restartSidecar } from "./bridge.js";
import FlashcardView from "./FlashcardView.vue";
import LibraryView from "./LibraryView.vue";
import PaperView from "./PaperView.vue";
import VaultView from "./VaultView.vue";

const PrototypeView = import.meta.env.DEV
  ? defineAsyncComponent(() => import("./PrototypeView.vue"))
  : null;
const showPrototype =
  import.meta.env.DEV &&
  new URLSearchParams(window.location.search).get("prototype") === "1";
const status = ref({ state: "starting" });
const restarting = ref(false);
const destination = ref("paper");
const flashcardPath = ref(null);
const paperPath = ref(null);
const paperStartup = ref(null);
const vaultStartup = ref(null);
const vaultReturnDestination = ref("paper");
const vaultCanCancel = ref(false);
let refreshTimer;

async function refreshStatus() {
  try {
    status.value = await getRuntimeStatus();
    if (status.value.state === "starting") {
      refreshTimer = window.setTimeout(refreshStatus, 200);
    }
  } catch {
    status.value = {
      state: "blocked",
      error: {
        code: "sidecar_unavailable",
        layer: "tauri_host",
        message: "无法读取本地运行状态。",
        recovery: "restart_sidecar",
      },
    };
  }
}

async function restart() {
  restarting.value = true;
  try {
    status.value = await restartSidecar();
    if (status.value.state === "ready") {
      destination.value = "paper";
      paperPath.value = null;
      flashcardPath.value = null;
      paperStartup.value = null;
      vaultStartup.value = null;
    }
  } catch (error) {
    status.value = {
      state: "blocked",
      error,
    };
  } finally {
    restarting.value = false;
  }
}

function blockRuntime(error) {
  status.value = { state: "blocked", error };
}

function openFlashcard(path) {
  flashcardPath.value = path;
  destination.value = "flashcard";
}

function openPaper(path) {
  paperPath.value = path;
  destination.value = "paper";
}

function openLibrary() {
  destination.value = "library";
}

function openVault(startup = null) {
  vaultReturnDestination.value = destination.value;
  vaultCanCancel.value = startup === null;
  vaultStartup.value = startup;
  destination.value = "vault";
}

function finishVault(startup) {
  paperStartup.value = startup;
  paperPath.value = null;
  vaultStartup.value = null;
  destination.value = "paper";
}

function cancelVault() {
  if (vaultCanCancel.value) {
    destination.value = vaultReturnDestination.value;
  }
}

onMounted(() => {
  if (!showPrototype) {
    refreshStatus();
  }
});
onUnmounted(() => window.clearTimeout(refreshTimer));
</script>

<template>
  <PrototypeView v-if="showPrototype" />

  <PaperView
    v-else-if="status.state === 'ready' && destination === 'paper'"
    :runtime="status"
    :initial-path="paperPath"
    :initial-startup="paperStartup"
    @runtime-blocked="blockRuntime"
    @open-flashcard="openFlashcard"
    @open-library="openLibrary"
    @open-vault="openVault"
    @startup-consumed="paperStartup = null"
  />

  <FlashcardView
    v-else-if="status.state === 'ready' && destination === 'flashcard'"
    :runtime="status"
    :initial-path="flashcardPath"
    @runtime-blocked="blockRuntime"
    @open-paper="openPaper"
    @open-library="openLibrary"
  />

  <LibraryView
    v-else-if="status.state === 'ready' && destination === 'library'"
    :runtime="status"
    @runtime-blocked="blockRuntime"
    @open-paper="openPaper"
    @open-flashcard="openFlashcard"
    @open-vault="openVault"
  />

  <VaultView
    v-else-if="status.state === 'ready' && destination === 'vault'"
    :runtime="status"
    :initial-startup="vaultStartup"
    :can-cancel="vaultCanCancel"
    @runtime-blocked="blockRuntime"
    @ready="finishVault"
    @cancel="cancelVault"
  />

  <main v-else class="runtime-gate" aria-live="polite">
    <section v-if="status.state === 'starting'" class="runtime-panel">
      <p class="eyebrow">Road v0.4 · CP4</p>
      <h1>正在启动本地 Core</h1>
      <p>窗口会在握手完成后解除阻塞。</p>
    </section>

    <section v-else class="runtime-panel runtime-error">
      <p class="eyebrow">本地运行边界已阻塞</p>
      <h1>无法安全连接 Python Core</h1>
      <p>{{ status.error?.message ?? "Sidecar 已停止。" }}</p>
      <dl v-if="status.error">
        <div>
          <dt>错误码</dt>
          <dd>{{ status.error.code }}</dd>
        </div>
        <div>
          <dt>层级</dt>
          <dd>{{ status.error.layer }}</dd>
        </div>
        <div>
          <dt>恢复</dt>
          <dd>{{ status.error.recovery }}</dd>
        </div>
      </dl>
      <button type="button" :disabled="restarting" @click="restart">
        {{ restarting ? "正在重启…" : "重启本地 Core" }}
      </button>
    </section>
  </main>
</template>

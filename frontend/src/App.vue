<script setup>
import { defineAsyncComponent, onMounted, onUnmounted, ref } from "vue";

import { bridgeRequest, getRuntimeStatus, restartSidecar } from "./bridge.js";
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
const paperPath = ref(null);
const paperStartup = ref(null);
const vaultStartup = ref(null);
const vaultReturnDestination = ref("paper");
const vaultCanCancel = ref(false);
const libraryContextGeneration = ref(0);
const pendingIntent = ref(null);
let refreshTimer;

const durableMethods = new Set([
  "vault.open",
  "vault.initialize",
  "vault.relocate",
  "migration.run",
  "paper.save",
  "paper.soft_delete",
  "library.rebuild",
  "library.move",
  "library.branch",
  "library.soft_delete",
  "library.restore",
  "library.permanently_delete",
  "library.create_folder",
  "library.rename_folder",
  "library.merge_folders",
  "library.soft_delete_folder",
  "library.restore_folder",
  "library.permanently_delete_folder",
]);

function cloneIntent(value) {
  return globalThis.structuredClone
    ? globalThis.structuredClone(value)
    : JSON.parse(JSON.stringify(value));
}

async function appRequest(method, params = {}, intent = null) {
  const durable = durableMethods.has(method);
  if (durable) {
    pendingIntent.value = cloneIntent(intent ?? {
      family: method.split(".")[0],
      method,
      vault_locator: params.vault_locator ?? null,
      summary: { fields: Object.keys(params).sort() },
    });
  }
  try {
    const result = await bridgeRequest(method, params);
    if (durable) pendingIntent.value = null;
    return result;
  } catch (error) {
    if (durable && error?.code !== "commit_unknown") pendingIntent.value = null;
    throw error;
  }
}

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
      paperStartup.value = null;
      vaultStartup.value = null;
      libraryContextGeneration.value += 1;
      if (
        pendingIntent.value?.family?.startsWith("library")
        || pendingIntent.value?.family === "index"
      ) {
        destination.value = "library";
      } else if (["vault", "migration"].includes(pendingIntent.value?.family)) {
        destination.value = "vault";
      }
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

function openPaper(path) {
  paperPath.value = path;
  destination.value = "paper";
}

function openLibrary() {
  destination.value = "library";
}

function openVault(startup = null, returnPaperPath = undefined) {
  vaultReturnDestination.value = destination.value;
  vaultCanCancel.value = startup === null;
  vaultStartup.value = startup;
  if (returnPaperPath !== undefined) {
    paperPath.value = returnPaperPath;
  }
  destination.value = "vault";
}

function finishVault(startup) {
  paperStartup.value = startup;
  paperPath.value = null;
  vaultStartup.value = null;
  libraryContextGeneration.value += 1;
  destination.value = (
    pendingIntent.value?.family?.startsWith("library")
    || pendingIntent.value?.family === "index"
  ) ? "library" : "paper";
}

function cancelVault() {
  if (vaultCanCancel.value) {
    destination.value = vaultReturnDestination.value;
  }
}

function settleIntent() {
  pendingIntent.value = null;
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

  <template v-else-if="status.state === 'ready'">
    <PaperView
      v-if="destination === 'paper'"
      :runtime="status"
      :initial-path="paperPath"
      :initial-startup="paperStartup"
      :pending-intent="pendingIntent"
      :request="appRequest"
      @runtime-blocked="blockRuntime"
      @open-library="openLibrary"
      @open-vault="openVault"
      @startup-consumed="paperStartup = null"
      @intent-settled="settleIntent"
    />

    <KeepAlive :key="libraryContextGeneration">
      <LibraryView
        v-if="destination === 'library'"
        :runtime="status"
        :pending-intent="pendingIntent"
        :request="appRequest"
        @runtime-blocked="blockRuntime"
        @open-paper="openPaper"
        @open-vault="openVault"
        @intent-settled="settleIntent"
      />
    </KeepAlive>

    <VaultView
      v-if="destination === 'vault'"
      :runtime="status"
      :initial-startup="vaultStartup"
      :can-cancel="vaultCanCancel"
      :pending-intent="pendingIntent"
      :request="appRequest"
      @runtime-blocked="blockRuntime"
      @ready="finishVault"
      @cancel="cancelVault"
      @intent-settled="settleIntent"
    />
  </template>

  <main v-else class="runtime-gate" aria-live="polite">
    <section v-if="status.state === 'starting'" class="runtime-panel">
      <p class="eyebrow">Local desktop · Python sidecar</p>
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

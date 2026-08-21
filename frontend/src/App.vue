<script setup>
import {
  computed,
  defineAsyncComponent,
  nextTick,
  onMounted,
  onUnmounted,
  ref,
} from "vue";

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
const paperView = ref(null);
const paperRenderGeneration = ref(0);
const workSurface = ref(null);
const shellNavigating = ref(false);
const shellBlocked = computed(() => shellNavigating.value || pendingIntent.value !== null);
const blockedCopy = computed(() => {
  const code = status.value.error?.code;
  if (code === "commit_unknown") {
    return {
      title: "写入结果暂时无法确认",
      happened: "本地 Core 在持久操作返回前失去连接；磁盘可能已提交，也可能未提交。",
      untouched: "阻塞页不会继续改写 Markdown 或 index.json，也不会自动重放这次持久操作。",
      next: "重启本地 Core；重启后会返回对应工作面，从磁盘重新读取或核对结果。",
    };
  }
  if (code === "protocol_mismatch") {
    return {
      title: "本地 Core 协议无法安全核对",
      happened: "App 与 Python Core 的协议版本或响应结构不一致，连接已停止。",
      untouched: "阻塞页没有修改 Markdown 或 index.json，也不会自动重放任何持久操作。",
      next: "重启本地 Core；成功后回到安全工作面。若再次出现，请退出并重新打开同一版本的 app。",
    };
  }
  if (code === "sidecar_unavailable") {
    return {
      title: "本地 Core 暂时不可用",
      happened: "Python Core 未启动、已退出，或没有在时限内响应。",
      untouched: "阻塞页没有修改 Markdown 或 index.json，也不会自动重放任何持久操作。",
      next: "重启本地 Core；成功后回到安全工作面。若仍失败，请退出并重新打开 app。",
    };
  }
  return {
    title: "本地运行边界已阻塞",
    happened: "keikeu 无法核对本地 Core 当前状态，因此停止进入工作面。",
    untouched: "阻塞页没有修改 Markdown 或 index.json，也不会自动重放任何持久操作。",
    next: "重启本地 Core；成功后回到安全工作面，再继续操作。",
  };
});
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
  if (shellBlocked.value) return;
  paperPath.value = path;
  paperRenderGeneration.value += 1;
  destination.value = "paper";
  void focusWorkSurface();
}

function openLibrary() {
  destination.value = "library";
  void focusWorkSurface();
}

function openVault(startup = null, returnPaperPath = undefined) {
  vaultReturnDestination.value = destination.value;
  vaultCanCancel.value = startup === null;
  vaultStartup.value = startup;
  if (returnPaperPath !== undefined) {
    paperPath.value = returnPaperPath;
  }
  destination.value = "vault";
  void focusWorkSurface();
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
  void focusWorkSurface();
}

function cancelVault() {
  if (vaultCanCancel.value) {
    destination.value = vaultReturnDestination.value;
    void focusWorkSurface();
  }
}

function settleIntent() {
  pendingIntent.value = null;
}

function recordPaperPath(path) {
  paperPath.value = path;
}

async function focusWorkSurface() {
  await nextTick();
  workSurface.value?.focus();
}

async function runShellIntent(action) {
  if (shellBlocked.value) return false;
  const trigger = document.activeElement;
  shellNavigating.value = true;
  try {
    if (
      destination.value === "paper"
      && paperView.value
      && !(await paperView.value.confirmDeparture())
    ) {
      shellNavigating.value = false;
      await nextTick();
      trigger?.focus?.();
      return false;
    }
    await action();
    await focusWorkSurface();
    return true;
  } finally {
    shellNavigating.value = false;
  }
}

function showPaper() {
  if (destination.value === "paper") return;
  return runShellIntent(() => { destination.value = "paper"; });
}

function showLibrary() {
  if (destination.value === "library") return;
  return runShellIntent(() => { destination.value = "library"; });
}

function startNewPaper() {
  return runShellIntent(() => {
    paperPath.value = null;
    paperStartup.value = null;
    paperRenderGeneration.value += 1;
    destination.value = "paper";
  });
}

function showVault() {
  if (destination.value === "vault") return;
  return runShellIntent(() => openVault(null, paperPath.value));
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

  <div v-else-if="status.state === 'ready'" class="app-shell">
    <header class="app-shellbar">
      <strong class="app-shell-brand">keikeu</strong>
      <nav class="app-shell-daily" aria-label="日常位置">
        <button
          type="button"
          :aria-current="destination === 'paper' ? 'page' : undefined"
          :disabled="shellBlocked"
          @click="showPaper"
        >Paper</button>
        <button
          type="button"
          :aria-current="destination === 'library' ? 'page' : undefined"
          :disabled="shellBlocked"
          @click="showLibrary"
        >Library</button>
      </nav>
      <div class="app-shell-actions" role="group" aria-label="工作区动作与环境">
        <button type="button" :disabled="shellBlocked" @click="startNewPaper">
          新 Paper
        </button>
        <button
          type="button"
          :aria-current="destination === 'vault' ? 'page' : undefined"
          :disabled="shellBlocked"
          @click="showVault"
        >Vault</button>
      </div>
    </header>

    <div
      ref="workSurface"
      class="app-work-surface"
      role="region"
      :aria-label="`${destination === 'paper' ? 'Paper' : destination === 'library' ? 'Library' : 'Vault'} 工作面`"
      tabindex="-1"
    >
      <PaperView
        v-if="destination === 'paper'"
        :key="paperRenderGeneration"
        ref="paperView"
        :runtime="status"
        :initial-path="paperPath"
        :initial-startup="paperStartup"
        :pending-intent="pendingIntent"
        :request="appRequest"
        @runtime-blocked="blockRuntime"
        @open-library="openLibrary"
        @open-vault="openVault"
        @paper-path-change="recordPaperPath"
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
    </div>
  </div>

  <main v-else class="runtime-gate" aria-live="polite">
    <section v-if="status.state === 'starting'" class="runtime-panel">
      <p class="eyebrow">Local desktop · Python sidecar</p>
      <h1>正在启动本地 Core</h1>
      <p>窗口会在握手完成后解除阻塞。</p>
    </section>

    <section
      v-else
      class="runtime-panel runtime-error"
      aria-labelledby="runtime-blocked-title"
    >
      <p class="eyebrow">本地运行边界已阻塞</p>
      <h1 id="runtime-blocked-title">{{ blockedCopy.title }}</h1>
      <p>{{ status.error?.message ?? "Sidecar 已停止。" }}</p>
      <dl class="runtime-guidance">
        <div>
          <dt>发生了什么</dt>
          <dd>{{ blockedCopy.happened }}</dd>
        </div>
        <div>
          <dt>保持原样</dt>
          <dd>{{ blockedCopy.untouched }}</dd>
        </div>
        <div>
          <dt>安全下一步</dt>
          <dd>{{ blockedCopy.next }}</dd>
        </div>
      </dl>
      <dl v-if="status.error" class="runtime-technical">
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

<style scoped>
.app-shell {
  min-height: 100vh;
  background: var(--canvas);
}

.app-shellbar {
  position: sticky;
  z-index: 20;
  top: 0;
  display: grid;
  grid-template-columns: auto auto minmax(20px, 1fr) auto;
  min-height: 56px;
  align-items: stretch;
  gap: 20px;
  padding: 0 26px;
  border-bottom: 1px solid var(--rule);
  background: var(--paper);
}

.app-shell-brand {
  align-self: center;
  font: 600 1.2rem var(--font-display);
}

.app-shell-daily,
.app-shell-actions {
  display: flex;
  align-items: stretch;
  gap: 4px;
}

.app-shell-actions {
  grid-column: 4;
}

.app-shellbar button {
  min-height: 44px;
  padding: 0 12px;
  border: 0;
  border-bottom: 3px solid transparent;
  color: var(--muted);
  background: transparent;
  cursor: pointer;
}

.app-shellbar button[aria-current="page"] {
  border-bottom-color: var(--ink);
  color: var(--ink);
  font-weight: 750;
}

.app-shellbar button:disabled {
  cursor: wait;
  opacity: .55;
}

.app-work-surface {
  min-width: 0;
}

.runtime-guidance dd {
  font-family: inherit;
}

@media (max-width: 760px) {
  .app-shellbar {
    grid-template-columns: auto 1fr;
    gap: 0 12px;
    padding: 8px 14px;
  }

  .app-shell-daily {
    justify-self: end;
  }

  .app-shell-actions {
    grid-column: 1 / -1;
    justify-content: flex-end;
  }
}
</style>

<script setup>
import {
  computed,
  defineAsyncComponent,
  nextTick,
  onMounted,
  onUnmounted,
  ref,
} from "vue";

import {
  bridgeRequest,
  confirmAction,
  getRuntimeStatus,
  registerWindowCloseGuard,
  restartSidecar,
} from "./bridge.js";
import CoreWorkspace from "./CoreWorkspace.vue";
import LibraryView from "./LibraryView.vue";
import PaperView from "./PaperView.vue";
import VaultView from "./VaultView.vue";

const PrototypeView = import.meta.env.DEV
  ? defineAsyncComponent(() => import("./PrototypeView.vue"))
  : null;
const showPrototype =
  import.meta.env.DEV &&
  new URLSearchParams(window.location.search).get("prototype") === "1";
const capabilities = ref(null);
const hostError = ref(null);
const storageError = ref("");
const storageBusy = ref(false);
const retryHost = () => window.location.reload();
const hostZh = (navigator.language ?? "").startsWith("zh");
const coreWorkspace = ref(null);
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
const closeError = ref("");
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
let unlistenClose;
let appUnmounted = false;
let durableRequests = 0;

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
    durableRequests += 1;
  }
  try {
    const cap = capabilities.value;
    const scope = cap?.storage_id ? { storage_id: cap.storage_id, generation: cap.generation } : {};
    const result = await bridgeRequest(method, { ...params, ...scope });
    if (cap && (capabilities.value?.storage_id !== cap.storage_id || capabilities.value?.generation !== cap.generation)) {
      throw { code: "stale_session" };
    }
    if (durable) pendingIntent.value = null;
    return result;
  } catch (error) {
    if (durable && error?.code !== "commit_unknown") pendingIntent.value = null;
    throw error;
  } finally {
    if (durable) durableRequests -= 1;
  }
}

async function requestWindowClose() {
  if (storageBusy.value) return false;
  if (capabilities.value?.backend === "rust") return coreWorkspace.value ? coreWorkspace.value.confirmDeparture() : false;
  closeError.value = "";
  if (appUnmounted || durableRequests || restarting.value || shellNavigating.value) return false;
  const intent = pendingIntent.value;
  let allowed;
  try {
    if (intent) {
      const hasDraft = intent.family === "paper_save";
      allowed = await confirmAction(
        hasDraft
          ? "上次保存结果仍未确认。关闭将放弃仅保存在内存中的草稿，且不会撤销可能已完成的保存。要放弃草稿并关闭吗？"
          : "上次写入结果仍未确认。关闭将放弃本次操作记录，且不会撤销可能已完成的磁盘操作。要放弃记录并关闭吗？",
        { okLabel: hasDraft ? "放弃草稿并关闭" : "放弃记录并关闭", cancelLabel: "留下核对" },
      );
    } else {
      allowed = paperView.value ? await paperView.value.confirmDeparture() : true;
    }
  } catch {
    closeError.value = "无法确认关闭；草稿和操作记录仍保留，请重试。";
    return false;
  }
  // A dialog answer belongs to the state it described. Keep snapshots until destruction succeeds.
  return allowed && !appUnmounted && !durableRequests && !restarting.value
    && !shellNavigating.value && pendingIntent.value === intent;
}

async function installCloseGuard() {
  if (unlistenClose) return true;
  try {
    const unlisten = await registerWindowCloseGuard(requestWindowClose);
    if (appUnmounted) {
      unlisten();
      return false;
    }
    unlistenClose = unlisten;
    return true;
  } catch {
    blockRuntime({
      code: "close_guard_unavailable",
      layer: "vue_ui",
      message: "关闭保护未能启动；工作面尚未打开，请重试。",
      recovery: "retry",
    });
    return false;
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
    if (!(await installCloseGuard())) return;
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

async function switchStorage(locale = null) {
  const zh = locale ? locale === "zh-CN" : hostZh;
  if (storageBusy.value || shellBlocked.value || durableRequests || restarting.value) return;
  storageBusy.value = true; storageError.value = "";
  const cap = capabilities.value;
  const kind = cap.storage_kind === "icloud" ? "local" : "icloud";
  try {
    const editor = cap.backend === "rust" ? coreWorkspace.value : paperView.value;
    if (editor && !(await editor.confirmDeparture())) return;
    if (pendingIntent.value || durableRequests || shellNavigating.value) return;
    const scope = { storage_id: cap.storage_id, generation: cap.generation };
    const inspection = await bridgeRequest("host.storage.inspect", { ...scope, kind });
    const description = kind === "icloud"
      ? (zh ? "打开 iCloud 中的 keikeu 工作区？首次使用会创建工作区。本机稿件不会自动搬入。" : "Open the keikeu workspace in iCloud? First use creates the workspace. Local Papers stay in local storage.")
      : (zh ? "返回本机存储？云端稿件与本机恢复记录会保留。" : "Return to local storage? Cloud Papers and local recovery records are retained.");
    if (!(await confirmAction(description))) return;
    if (capabilities.value !== cap || pendingIntent.value || durableRequests || shellNavigating.value) return;
    // Recheck the editor after the system dialog, including changes typed while it was open.
    if (editor && !(await editor.confirmDeparture())) return;
    const selected = await bridgeRequest("host.storage.select", { ...scope, token: inspection.token });
    window.clearTimeout(refreshTimer);
    capabilities.value = selected;
    paperPath.value = null; paperStartup.value = null; vaultStartup.value = null;
    destination.value = "paper"; paperRenderGeneration.value += 1; libraryContextGeneration.value += 1;
    if (selected.backend === "rust") status.value = { state: "ready" };
    else await refreshStatus();
  } catch (e) { storageError.value = `${zh ? "切换未完成" : "Switch incomplete"}: ${e?.code ?? "operation_failed"}`; }
  finally { storageBusy.value = false; }
}

onMounted(async () => {
  if (!showPrototype && await installCloseGuard()) {
    try {
      capabilities.value = await bridgeRequest("host.capabilities");
      if (capabilities.value?.backend === "rust") status.value = { state: "ready" };
      else await refreshStatus();
    } catch (error) { hostError.value = error; blockRuntime(error); }
  }
});
onUnmounted(() => {
  appUnmounted = true;
  window.clearTimeout(refreshTimer);
  unlistenClose?.();
});
</script>

<template>
  <PrototypeView v-if="showPrototype" />

  <main v-else-if="hostError" class="runtime-gate" role="alert">
    <section class="runtime-panel runtime-error">
      <h1>{{ hostZh ? '本机存储未能打开' : 'Local storage could not open' }}</h1>
      <p>{{ hostZh ? '现有稿件和恢复记录保持原样。请退出并重新打开 app，再检查本机存储状态。' : 'Existing Papers and recovery records remain unchanged. Quit and reopen the app to check local storage again.' }}</p>
      <p>{{ hostError.code ?? 'host_unavailable' }}</p>
      <button @click="retryHost">{{ hostZh ? '重新检查' : 'Check again' }}</button>
    </section>
  </main>

  <CoreWorkspace v-else-if="capabilities?.backend === 'rust'" :key="`${capabilities.storage_id}:${capabilities.generation}`" ref="coreWorkspace" :capabilities="capabilities" :inert="storageBusy">
    <template #storage="{ locale }">
      <button :disabled="storageBusy || shellBlocked" @click="switchStorage(locale)">{{ capabilities.storage_kind === 'icloud' ? (locale === 'zh-CN' ? '切换到本机' : 'Use local storage') : (locale === 'zh-CN' ? '选择 iCloud' : 'Choose iCloud') }}</button>
      <span v-if="storageError" role="alert">{{ storageError }}</span>
    </template>
  </CoreWorkspace>

  <div v-else-if="status.state === 'ready'" class="app-shell" :inert="storageBusy">
    <header class="app-shellbar">
      <strong class="app-shell-brand">keikeu</strong>
      <button v-if="capabilities?.methods?.includes('host.storage.select')" :disabled="storageBusy || shellBlocked" @click="switchStorage()">选择 iCloud</button>
      <span v-if="storageError" role="alert">{{ storageError }}</span>
      <nav class="app-shell-daily" aria-label="日常位置">
        <button
          type="button"
          :aria-current="destination === 'paper' ? 'page' : undefined"
          :disabled="shellBlocked"
          @click="showPaper"
        >编辑 Paper</button>
        <button
          type="button"
          class="app-shell-new-paper"
          :disabled="shellBlocked"
          @click="startNewPaper"
        >新 Paper</button>
        <button
          type="button"
          :aria-current="destination === 'library' ? 'page' : undefined"
          :disabled="shellBlocked"
          @click="showLibrary"
        >Library</button>
      </nav>
      <button
        type="button"
        class="app-shell-context"
        :aria-current="destination === 'vault' ? 'page' : undefined"
        :disabled="shellBlocked"
        @click="showVault"
      >Vault</button>
    </header>

    <div
      ref="workSurface"
      class="app-work-surface"
      role="region"
      :aria-label="`${destination === 'paper' ? '编辑 Paper' : destination === 'library' ? 'Library' : 'Vault'} 工作面`"
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
  <p v-if="closeError" role="alert" class="runtime-panel">{{ closeError }}</p>
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
  grid-template-rows: 56px;
  height: 56px;
  align-items: stretch;
  gap: 16px;
  padding: 0 22px;
  border-bottom: 1px solid var(--rule);
  background: var(--paper);
}

.app-shell-brand {
  align-self: center;
  font: 700 1.125rem/1.375rem var(--font-body);
}

.app-shell-daily {
  display: flex;
  align-items: stretch;
  gap: 4px;
  white-space: nowrap;
}

.app-shell-context {
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
  white-space: nowrap;
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

@media (min-width: 800px) {
  .app-shell-new-paper {
    min-width: 110px;
  }
}

@media (max-width: 799px) {
  .app-shellbar {
    grid-template-columns: auto auto minmax(0, 1fr) auto;
    gap: 0 4px;
    padding: 0 12px;
  }

  .app-shell-daily {
    grid-column: 2;
    grid-row: 1;
  }

  .app-shell-context {
    grid-column: 4;
    grid-row: 1;
  }

  .app-shellbar button {
    padding-inline: 6px;
  }
}

@media (max-width: 479px) {
  .app-shellbar {
    gap: 0 2px;
    padding-inline: 8px;
  }

  .app-shell-daily {
    gap: 2px;
  }

  .app-shellbar button {
    padding-inline: 4px;
  }
}
</style>

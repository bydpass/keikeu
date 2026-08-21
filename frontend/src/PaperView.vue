<script setup>
import { computed, onMounted, onUnmounted, ref } from "vue";

import PaperV4Workbench from "./PaperV4Workbench.vue";
import {
  bridgeRequest,
  confirmDiscardChanges,
  openSystemTarget,
  registerWindowCloseGuard,
} from "./bridge.js";

const props = defineProps({
  runtime: { type: Object, required: true },
  initialPath: { type: String, default: null },
  initialStartup: { type: Object, default: null },
  pendingIntent: { type: Object, default: null },
  request: { type: Function, default: bridgeRequest },
});
const emit = defineEmits([
  "runtime-blocked",
  "open-library",
  "open-vault",
  "paper-path-change",
  "startup-consumed",
  "intent-settled",
]);

const screen = ref("loading");
const startup = ref(null);
const paper = ref(null);
const repair = ref(null);
const baselineEditable = ref(undefined);
const workbenchState = ref("ready");
const dirty = ref(false);
const busy = ref(false);
const saving = ref(false);
const notice = ref("");
const error = ref(null);
const deleteDialog = ref(null);
let dailyTimer;
let unlistenClose;
let hasObservedDirty = false;

const savedPath = computed(() => paper.value?.path ?? null);
const hasPendingSave = computed(() => props.pendingIntent?.family === "paper_save");

function normalizeError(value) {
  return value && typeof value === "object"
    ? {
        code: value.code ?? "operation_failed",
        layer: value.layer ?? "vue_ui",
        message: value.message ?? "本地操作未完成。",
        recovery: value.recovery ?? "review",
      }
    : {
        code: "operation_failed",
        layer: "vue_ui",
        message: "本地操作未完成。",
        recovery: "review",
      };
}

function handleError(raw, fallback) {
  const normalized = normalizeError(raw);
  error.value = { ...normalized, message: `${fallback}：${normalized.message}` };
  if (
    ["commit_unknown", "protocol_mismatch", "sidecar_unavailable"].includes(
      normalized.code,
    )
  ) {
    emit("runtime-blocked", error.value);
  }
  return normalized;
}

function editable(value) {
  return {
    display_name: value.display_name,
    tags: [...value.tags],
    pages: value.pages.map(({ name, content, type }) => ({ name, content, type })),
  };
}

function applyPaper(value, { baseline, indexState = "current" } = {}) {
  paper.value = value;
  emit("paper-path-change", value.path ?? null);
  baselineEditable.value = baseline;
  repair.value = null;
  workbenchState.value = indexState === "degraded" ? "index_degraded" : "ready";
  error.value = null;
  screen.value = "editor";
}

function retainedDraft(intent) {
  return {
    ...intent.save,
    path: intent.reconcile.source_digest === null ? null : intent.reconcile.target_path,
    edit_token: "expired-after-restart",
    code: intent.reconcile.code,
    created: intent.reconcile.created,
    updated: intent.reconcile.created,
    target_path: intent.reconcile.target_path,
    source_digest: intent.reconcile.source_digest,
  };
}

async function reconcilePendingSave(intent) {
  const result = await props.request("paper.reconcile_save", intent.reconcile);
  if (["committed", "not_committed"].includes(result.state) && result.paper) {
    applyPaper(result.paper, {
      baseline:
        result.state === "not_committed" ? intent.reconcile.baseline : undefined,
      indexState: result.index_state,
    });
    notice.value = result.state === "committed"
      ? "已确认上次保存落盘。"
      : "已确认上次保存未落盘；草稿仍在，请检查后重新保存。";
  } else {
    paper.value = retainedDraft(intent);
    emit("paper-path-change", paper.value.path ?? null);
    baselineEditable.value = intent.reconcile.baseline;
    repair.value = result.repair ?? null;
    workbenchState.value = result.state === "repair_required"
      ? "repair_required"
      : "stale";
    screen.value = "editor";
    notice.value = result.state === "repair_required"
      ? "磁盘 Paper 需要人工修复；草稿仍在且保存已禁用。"
      : `磁盘状态无法与草稿自动合并（${result.stale_reason ?? "stale"}）。`;
  }
  if (["committed", "not_committed"].includes(result.state)) {
    emit("intent-settled");
  }
}

async function openInitialPaper() {
  if (props.pendingIntent?.family === "paper_save") {
    await reconcilePendingSave(props.pendingIntent);
    return;
  }
  if (props.pendingIntent?.family === "paper_delete") {
    await props.request("library.query", {
      scope: "trash",
      search: "",
      sort: "updated_desc",
      verify_index: true,
    });
    emit("intent-settled");
    notice.value = "已在重启后重新读取废纸篓；请据磁盘结果确认上次删除。";
  }
  if (!props.initialPath) {
    applyPaper(await props.request("paper.create_draft", {}));
    return;
  }
  const result = await props.request("paper.open", { path: props.initialPath });
  if (result.state === "opened" && result.paper) {
    applyPaper(result.paper);
    return;
  }
  repair.value = result.repair;
  screen.value = "repair";
}

async function enterWorkspace() {
  window.clearTimeout(dailyTimer);
  busy.value = true;
  screen.value = "loading";
  try {
    await openInitialPaper();
  } catch (raw) {
    screen.value = "error";
    handleError(raw, "无法打开 Paper 工作面");
  } finally {
    busy.value = false;
  }
}

async function loadStartup() {
  try {
    startup.value = props.initialStartup ?? await props.request("startup.load", {});
    if (props.initialStartup) emit("startup-consumed");
    if (startup.value.state !== "ready") {
      screen.value = "startup_gate";
      emit("open-vault", startup.value);
      return;
    }
    if (startup.value.show_daily_card) {
      screen.value = "daily";
      dailyTimer = window.setTimeout(enterWorkspace, 1200);
    } else {
      await enterWorkspace();
    }
  } catch (raw) {
    screen.value = "error";
    handleError(raw, "无法读取启动状态");
  }
}

async function requestDeparture(action) {
  if (busy.value || saving.value) return false;
  if (dirty.value || hasPendingSave.value) {
    try {
      if (!(await confirmDiscardChanges())) return false;
    } catch (raw) {
      handleError(raw, "无法确认是否放弃更改");
      return false;
    }
  }
  if (hasPendingSave.value) emit("intent-settled");
  await action?.();
  return true;
}

function openLibrary() {
  requestDeparture(() => emit("open-library"));
}

function updateDirty(value) {
  const wasDirty = dirty.value;
  dirty.value = value;
  if (hasObservedDirty && value && !wasDirty) notice.value = "";
  hasObservedDirty = true;
}

async function revealRepair() {
  if (!repair.value?.path) return;
  try {
    await openSystemTarget("reveal", repair.value.path);
  } catch (raw) {
    handleError(raw, "无法在 Finder 中显示 Paper");
  }
}

async function recheckOpenRepair() {
  if (busy.value || !repair.value?.path) return;
  busy.value = true;
  try {
    const result = await props.request("paper.open", { path: repair.value.path });
    if (result.state === "opened" && result.paper) {
      applyPaper(result.paper);
      notice.value = "Paper 结构已通过重新检查。";
    } else {
      repair.value = result.repair;
      notice.value = "Paper 仍需人工修复；app 没有改写文件。";
    }
  } catch (raw) {
    handleError(raw, "无法重新检查 Paper");
  } finally {
    busy.value = false;
  }
}

async function recheckUnknownSave() {
  if (busy.value || !hasPendingSave.value) return;
  busy.value = true;
  try {
    await reconcilePendingSave(props.pendingIntent);
  } catch (raw) {
    handleError(raw, "无法重新检查未知保存");
  } finally {
    busy.value = false;
  }
}

async function copyRetainedDraft() {
  const submitted = props.pendingIntent?.reconcile?.submitted;
  if (!submitted) return;
  try {
    await navigator.clipboard.writeText(JSON.stringify(submitted, null, 2));
    notice.value = "保留草稿已复制；没有写入 Vault。";
  } catch (raw) {
    handleError(raw, "无法复制保留草稿");
  }
}

async function savePaper(submitted) {
  if (busy.value || saving.value || !paper.value) return;
  const baseline = paper.value.source_digest === null ? null : editable(paper.value);
  const save = {
    edit_token: paper.value.edit_token,
    vault_locator: paper.value.vault_locator,
    display_name: submitted.display_name,
    tags: submitted.tags,
    pages: submitted.pages,
  };
  const intent = {
    family: "paper_save",
    method: "paper.save",
    vault_locator: paper.value.vault_locator,
    summary: { code: paper.value.code, target_path: paper.value.target_path },
    save,
    reconcile: {
      vault_locator: paper.value.vault_locator,
      target_path: paper.value.target_path,
      code: paper.value.code,
      created: paper.value.created,
      source_digest: paper.value.source_digest,
      baseline,
      submitted: {
        display_name: submitted.display_name,
        tags: submitted.tags,
        pages: submitted.pages,
      },
    },
  };
  saving.value = true;
  error.value = null;
  notice.value = "";
  try {
    const result = await props.request("paper.save", save, intent);
    applyPaper(result.paper, {
      indexState: result.warnings?.includes("index_degraded") ? "degraded" : "current",
    });
    notice.value = result.warnings?.includes("index_degraded")
      ? "Paper 已保存；Index 需要显式重建。"
      : "Paper 已保存为卡页 Markdown。";
  } catch (raw) {
    const normalized = handleError(raw, "无法保存 Paper");
    if (normalized.code === "stale_snapshot") workbenchState.value = "stale";
    if (normalized.code === "commit_unknown") workbenchState.value = "commit_unknown";
  } finally {
    saving.value = false;
  }
}

function showDeleteDialog() {
  if (busy.value || saving.value || !savedPath.value) return;
  if (typeof deleteDialog.value?.showModal === "function") {
    deleteDialog.value.showModal();
  } else if (deleteDialog.value) {
    deleteDialog.value.open = true;
  }
}

function closeDeleteDialog() {
  if (typeof deleteDialog.value?.close === "function") {
    deleteDialog.value.close();
  } else if (deleteDialog.value) {
    deleteDialog.value.open = false;
  }
}

async function deletePaper() {
  closeDeleteDialog();
  await requestDeparture(async () => {
    busy.value = true;
    try {
      const params = {
        edit_token: paper.value.edit_token,
        vault_locator: paper.value.vault_locator,
      };
      const result = await props.request("paper.soft_delete", params, {
        family: "paper_delete",
        method: "paper.soft_delete",
        vault_locator: paper.value.vault_locator,
        summary: { target_path: paper.value.target_path },
      });
      if (result.report.error) throw new Error(result.report.error);
      applyPaper(await props.request("paper.create_draft", {}), {
        indexState: result.warnings?.includes("index_degraded") ? "degraded" : "current",
      });
      notice.value = "整份 Paper 已移入废纸篓。";
    } catch (raw) {
      handleError(raw, "无法删除整份 Paper");
    } finally {
      busy.value = false;
    }
  });
}

function confirmDeparture() {
  return requestDeparture();
}

defineExpose({ confirmDeparture });

onMounted(async () => {
  await loadStartup();
  unlistenClose = await registerWindowCloseGuard(() => requestDeparture());
});
onUnmounted(() => {
  window.clearTimeout(dailyTimer);
  unlistenClose?.();
});
</script>

<template>
  <main class="paper-view">
    <section v-if="screen === 'daily'" class="paper-gate" aria-live="polite">
      <p>DAILY CARD</p>
      <h2>先留下一句，再决定它是什么。</h2>
      <button type="button" @click="enterWorkspace">开始写</button>
    </section>

    <section v-else-if="screen === 'loading'" class="paper-gate" aria-live="polite">
      <p>LOCAL RUNTIME</p>
      <h2>正在读取 Paper…</h2>
    </section>

    <section v-else-if="screen === 'repair'" class="paper-gate repair-panel">
      <p>REPAIR REQUIRED</p>
      <h2>这份 Paper 暂时不能安全打开</h2>
      <code>{{ repair?.path }}</code>
      <p>{{ repair?.reason }}</p>
      <p v-if="repair?.page_number">可确定的位置：第 {{ repair.page_number }} 页。</p>
      <div class="repair-actions">
        <button type="button" @click="revealRepair">在 Finder 中显示</button>
        <button type="button" :disabled="busy" @click="recheckOpenRepair">重新检查</button>
        <button type="button" @click="openLibrary">返回 Library</button>
      </div>
    </section>

    <section v-else-if="screen === 'error'" class="paper-gate repair-panel" role="alert">
      <p>{{ error?.code }}</p>
      <h2>{{ error?.message }}</h2>
    </section>

    <template v-else-if="screen === 'editor' && paper">
      <p v-if="notice" class="paper-notice" role="status">{{ notice }}</p>
      <p v-if="error" class="paper-error" role="alert">{{ error.message }}</p>
      <PaperV4Workbench
        :paper="paper"
        :baseline-editable="baselineEditable"
        :state="workbenchState"
        :saving="saving"
        :can-delete-whole-paper="Boolean(paper.path)"
        @dirty-change="updateDirty"
        @save="savePaper"
        @whole-delete="showDeleteDialog"
      />
      <details v-if="repair" class="repair-detail">
        <summary>人工修复信息</summary>
        <code>{{ repair.path }}</code>
        <p>{{ repair.reason }}</p>
        <p v-if="repair.page_number">可确定的位置：第 {{ repair.page_number }} 页。</p>
        <div class="repair-actions">
          <button type="button" @click="copyRetainedDraft">复制保留草稿</button>
          <button type="button" @click="revealRepair">在 Finder 中显示</button>
          <button type="button" :disabled="busy" @click="recheckUnknownSave">重新检查</button>
          <button type="button" class="quiet-danger" @click="openLibrary">
            放弃草稿并返回 Library
          </button>
        </div>
      </details>
    </template>

    <dialog ref="deleteDialog" class="delete-paper-dialog">
      <h2>删除整份 Paper？</h2>
      <p>确认后移入 Vault 废纸篓；不会永久删除。</p>
      <div>
        <button type="button" @click="closeDeleteDialog">取消</button>
        <button type="button" class="quiet-danger" @click="deletePaper">确认移入废纸篓</button>
      </div>
    </dialog>
  </main>
</template>

<style scoped>
.paper-view { min-height: calc(100vh - 56px); padding: 26px clamp(18px, 4vw, 54px) 48px; }
.paper-gate > p { margin: 0; color: var(--signal); font: 700 .68rem var(--font-mono); letter-spacing: .12em; }
button { min-height: 40px; padding: 8px 13px; border: 1px solid var(--rule); color: var(--ink); background: var(--paper); font: inherit; cursor: pointer; }
button:disabled { opacity: .55; cursor: wait; }
.quiet-danger { border-color: var(--danger); color: var(--danger); }
.paper-notice, .paper-error, .repair-detail { width: min(920px, 100%); margin: 0 auto 12px; padding: 10px 14px; border-left: 4px solid var(--signal); background: var(--paper); }
.paper-error, .repair-detail { border-left-color: var(--danger); background: var(--danger-soft); }
.paper-gate { width: min(620px, 100%); margin: 14vh auto 0; padding: 30px; border: 1px solid var(--rule); border-top: 5px solid var(--signal); background: var(--paper); }
.paper-gate h2 { font: 500 2rem var(--font-display); }
.repair-panel { border-top-color: var(--danger); }
.repair-actions { display: flex; flex-wrap: wrap; gap: 8px; }
.delete-paper-dialog { width: min(430px, calc(100% - 32px)); padding: 24px; border: 1px solid var(--rule); color: var(--ink); background: var(--paper); }
.delete-paper-dialog::backdrop { background: rgb(27 23 20 / .42); }
.delete-paper-dialog div { display: flex; justify-content: flex-end; gap: 8px; }
</style>

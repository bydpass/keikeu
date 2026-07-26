<script setup>
import { computed, onMounted, ref } from "vue";

import { bridgeRequest, chooseVaultDirectory } from "./bridge.js";

const props = defineProps({
  runtime: {
    type: Object,
    required: true,
  },
  initialStartup: {
    type: Object,
    default: null,
  },
  canCancel: {
    type: Boolean,
    default: false,
  },
});

const emit = defineEmits(["runtime-blocked", "ready", "cancel"]);

const mode = ref("picker");
const path = ref("");
const preview = ref(null);
const relocationDestination = ref("");
const relocationConfirmed = ref(false);
const migration = ref(null);
const migrationConfirmed = ref(false);
const migrationResult = ref(null);
const busyAction = ref("");
const error = ref(null);
const notice = ref("");

const busy = computed(() => busyAction.value !== "");

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
    message:
      normalized.code === "commit_unknown"
        ? "写入请求已经发出，但磁盘提交状态未知。请重启 Core，并重新检查 Vault。"
        : `${fallback}：${normalized.message}`,
  };
  if (
    normalized.layer === "tauri_host" &&
    ["commit_unknown", "protocol_mismatch", "sidecar_unavailable"].includes(
      normalized.code,
    )
  ) {
    emit("runtime-blocked", visible);
    return;
  }
  error.value = visible;
}

function isMigration(value) {
  return (
    value &&
    typeof value.token === "string" &&
    typeof value.ready === "boolean" &&
    typeof value.backup_path === "string" &&
    Number.isInteger(value.cache_count) &&
    Number.isInteger(value.trash_cache_count) &&
    Number.isInteger(value.outline_count) &&
    Number.isInteger(value.trash_outline_count) &&
    Array.isArray(value.issues) &&
    value.issues.every(
      (issue) =>
        typeof issue?.path === "string" &&
        typeof issue.message === "string",
    )
  );
}

function validatePreview(value) {
  if (
    !value ||
    typeof value.token !== "string" ||
    !["paper", "create", "relocate", "migration"].includes(value.kind) ||
    typeof value.display_path !== "string" ||
    !Number.isInteger(value.paper_count) ||
    typeof value.source_kind !== "string" ||
    typeof value.message !== "string" ||
    (value.kind === "migration" && !isMigration(value.migration))
  ) {
    throw {
      code: "operation_failed",
      layer: "vue_ui",
      message: "Vault 预览数据不完整。",
      recovery: "inspect",
    };
  }
  return value;
}

function validateStartup(value) {
  if (
    !value ||
    !["ready", "vault_picker", "migration"].includes(value.state) ||
    typeof value.show_daily_card !== "boolean" ||
    (value.state === "migration" && !isMigration(value.migration))
  ) {
    throw {
      code: "operation_failed",
      layer: "vue_ui",
      message: "启动状态数据不完整。",
      recovery: "restart_sidecar",
    };
  }
  return value;
}

function validateMigrationResult(value) {
  if (
    !value ||
    !Number.isInteger(value.converted_count) ||
    typeof value.backup_path !== "string" ||
    typeof value.report_path !== "string" ||
    !Array.isArray(value.paper_paths) ||
    value.paper_paths.some((item) => typeof item !== "string")
  ) {
    throw {
      code: "operation_failed",
      layer: "vue_ui",
      message: "迁移结果数据不完整。",
      recovery: "review",
    };
  }
  return value;
}

function showMigration(nextMigration) {
  if (!isMigration(nextMigration)) {
    throw {
      code: "operation_failed",
      layer: "vue_ui",
      message: "迁移预检数据不完整。",
      recovery: "inspect",
    };
  }
  migration.value = nextMigration;
  migrationConfirmed.value = false;
  mode.value = "migration";
}

function applyStartup(rawStartup) {
  const startup = validateStartup(rawStartup);
  if (startup.state === "ready") {
    emit("ready", startup);
    return;
  }
  if (startup.state === "migration") {
    showMigration(startup.migration);
    return;
  }
  mode.value = "picker";
  path.value = startup.configured_path ?? "";
  notice.value = startup.message ?? "";
  if (startup.preview) {
    applyPreview(startup.preview);
  }
}

function applyPreview(rawPreview) {
  const nextPreview = validatePreview(rawPreview);
  preview.value = nextPreview;
  path.value = nextPreview.display_path;
  error.value = null;
  notice.value = "";
  if (nextPreview.kind === "migration") {
    showMigration(nextPreview.migration);
    return;
  }
  mode.value = "preview";
}

function returnToPicker() {
  mode.value = "picker";
  preview.value = null;
  migration.value = null;
  migrationResult.value = null;
  relocationDestination.value = "";
  relocationConfirmed.value = false;
  migrationConfirmed.value = false;
  error.value = null;
  notice.value = "";
}

async function inspectVault() {
  if (busy.value) {
    return;
  }
  error.value = null;
  notice.value = "";
  busyAction.value = "inspect";
  try {
    applyPreview(await bridgeRequest("vault.inspect", { path: path.value }));
  } catch (rawError) {
    handleError(rawError, "无法检查 Vault");
  } finally {
    busyAction.value = "";
  }
}

async function chooseDirectory() {
  if (busy.value) {
    return;
  }
  error.value = null;
  busyAction.value = "choose";
  try {
    const selected = await chooseVaultDirectory();
    if (selected === null) {
      notice.value = "未选择文件夹；也可以手工输入完整路径。";
      return;
    }
    if (typeof selected !== "string") {
      throw {
        code: "operation_failed",
        layer: "vue_ui",
        message: "目录选择器返回了无效路径。",
        recovery: "choose_directory",
      };
    }
    path.value = selected;
    busyAction.value = "inspect";
    applyPreview(await bridgeRequest("vault.inspect", { path: path.value }));
  } catch (rawError) {
    handleError(rawError, "无法选择目录");
  } finally {
    busyAction.value = "";
  }
}

async function runStartupMutation(method, params, fallback) {
  if (busy.value) {
    return;
  }
  busyAction.value = method;
  error.value = null;
  notice.value = "";
  try {
    applyStartup(await bridgeRequest(method, params));
  } catch (rawError) {
    handleError(rawError, fallback);
  } finally {
    busyAction.value = "";
  }
}

function openPreview() {
  if (preview.value?.kind === "paper") {
    runStartupMutation(
      "vault.open",
      { preview_token: preview.value.token },
      "无法切换 Vault",
    );
  } else if (preview.value?.kind === "create") {
    runStartupMutation(
      "vault.initialize",
      { preview_token: preview.value.token },
      "无法初始化 Vault",
    );
  }
}

function relocateVault() {
  if (
    preview.value?.kind !== "relocate" ||
    !relocationConfirmed.value ||
    !relocationDestination.value.trim()
  ) {
    error.value = {
      code: "validation_failed",
      layer: "vue_ui",
      message: "请输入 Home 内全新目标路径，并确认只复制来源。",
      recovery: "correct_input",
    };
    return;
  }
  runStartupMutation(
    "vault.relocate",
    {
      preview_token: preview.value.token,
      destination_path: relocationDestination.value,
    },
    "无法复制、验证并切换 Vault",
  );
}

async function runMigration() {
  if (
    busy.value ||
    !migration.value?.ready ||
    !migrationConfirmed.value
  ) {
    return;
  }
  busyAction.value = "migration.run";
  error.value = null;
  notice.value = "";
  try {
    migrationResult.value = validateMigrationResult(
      await bridgeRequest("migration.run", {
        preflight_token: migration.value.token,
      }),
    );
    mode.value = "migration_result";
  } catch (rawError) {
    handleError(rawError, "迁移未完成；原 Vault 应保持可恢复状态");
  } finally {
    busyAction.value = "";
  }
}

async function openMigratedVault() {
  if (busy.value) {
    return;
  }
  busyAction.value = "startup.load";
  error.value = null;
  try {
    applyStartup(await bridgeRequest("startup.load", {}));
  } catch (rawError) {
    handleError(rawError, "无法打开已迁移 Vault");
  } finally {
    busyAction.value = "";
  }
}

onMounted(() => {
  if (props.initialStartup) {
    try {
      applyStartup(props.initialStartup);
    } catch (rawError) {
      handleError(rawError, "无法读取启动 gate");
    }
  }
});
</script>

<template>
  <main class="vault-gate">
    <section class="vault-panel" :aria-busy="busy">
      <header>
        <p class="vault-eyebrow">Road v0.4 · CP9</p>
        <h1>{{ mode.startsWith("migration") ? "迁移旧 Vault" : "打开或创建 Vault" }}</h1>
        <p>Paper Markdown 保留在本地；Vue 只提交路径与确认令牌。</p>
      </header>

      <template v-if="mode === 'picker'">
        <label>
          <span>Vault 文件夹路径</span>
          <input
            v-model="path"
            type="text"
            :disabled="busy"
            autocomplete="off"
            @input="error = null"
          >
        </label>
        <div class="vault-actions">
          <button type="button" :disabled="busy" @click="chooseDirectory">
            从系统选择文件夹
          </button>
          <button
            class="primary"
            type="button"
            :disabled="busy || !path.trim()"
            @click="inspectVault"
          >{{ busyAction === "inspect" ? "检查中…" : "检查 Vault" }}</button>
        </div>
      </template>

      <template v-else-if="mode === 'preview' && preview">
        <div class="vault-preview">
          <p class="preview-kind">{{ preview.kind }}</p>
          <code>{{ preview.display_path }}</code>

          <template v-if="preview.kind === 'paper'">
            <h2>检测到可用 Paper Vault</h2>
            <p>{{ preview.paper_count }} 个活动 Paper。确认后才切换本地配置。</p>
            <button class="primary" type="button" :disabled="busy" @click="openPreview">
              确认切换并打开
            </button>
          </template>

          <template v-else-if="preview.kind === 'create'">
            <h2>此位置为空或尚不存在</h2>
            <p>确认后将创建 Vault 目录、cache 与可重建索引。</p>
            <button class="primary" type="button" :disabled="busy" @click="openPreview">
              确认初始化并打开
            </button>
          </template>

          <template v-else-if="preview.kind === 'relocate'">
            <h2>来源不在允许写入的 Home 边界内</h2>
            <p>{{ preview.message }}</p>
            <p>只读识别：{{ preview.source_kind }} Vault。原路径不会被修改或删除。</p>
            <label>
              <span>Home 内全新目标路径</span>
              <input
                v-model="relocationDestination"
                type="text"
                :disabled="busy"
                autocomplete="off"
              >
            </label>
            <label class="vault-check">
              <input v-model="relocationConfirmed" type="checkbox" :disabled="busy">
              <span>我确认：仅复制并验证到新位置；原路径保持不变。</span>
            </label>
            <button
              class="primary"
              type="button"
              :disabled="busy || !relocationConfirmed || !relocationDestination.trim()"
              @click="relocateVault"
            >复制、验证并切换</button>
          </template>

          <button type="button" :disabled="busy" @click="returnToPicker">
            选择其他文件夹
          </button>
        </div>
      </template>

      <template v-else-if="mode === 'migration' && migration">
        <div class="migration-summary">
          <h2>迁移前检查</h2>
          <code>完整备份将写入：{{ migration.backup_path }}</code>
          <dl>
            <div><dt>活动 Cache</dt><dd>{{ migration.cache_count }}</dd></div>
            <div><dt>Trash Cache</dt><dd>{{ migration.trash_cache_count }}</dd></div>
            <div><dt>活动 Outline</dt><dd>{{ migration.outline_count }}</dd></div>
            <div><dt>Trash Outline</dt><dd>{{ migration.trash_outline_count }}</dd></div>
          </dl>
          <section v-if="migration.issues.length" class="migration-issues">
            <h3>迁移被以下项目阻止</h3>
            <ul>
              <li v-for="issue in migration.issues" :key="`${issue.path}:${issue.message}`">
                <strong>{{ issue.path }}</strong>
                <span>{{ issue.message }}</span>
              </li>
            </ul>
          </section>
          <p v-else>预检通过。执行时会先创建完整备份，再在 staging 中转换和验证。</p>
          <label v-if="migration.ready" class="vault-check">
            <input v-model="migrationConfirmed" type="checkbox" :disabled="busy">
            <span>我已了解：成功后旧 Outline 将从活动 Vault 与 Trash 永久移除。</span>
          </label>
          <div class="vault-actions">
            <button
              v-if="migration.ready"
              class="danger"
              type="button"
              :disabled="busy || !migrationConfirmed"
              @click="runMigration"
            >{{ busyAction === "migration.run" ? "正在备份并迁移…" : "创建完整备份并迁移" }}</button>
            <button type="button" :disabled="busy" @click="returnToPicker">
              选择其他文件夹
            </button>
          </div>
        </div>
      </template>

      <template v-else-if="mode === 'migration_result' && migrationResult">
        <div class="migration-result">
          <h2>迁移已完成</h2>
          <p>已转换 {{ migrationResult.converted_count }} 个 Paper。</p>
          <code>完整备份：{{ migrationResult.backup_path }}</code>
          <code>迁移报告：{{ migrationResult.report_path }}</code>
          <button class="primary" type="button" :disabled="busy" @click="openMigratedVault">
            打开已迁移的 Vault
          </button>
        </div>
      </template>

      <section v-if="error" class="vault-error" aria-live="assertive">
        <strong>{{ error.message }}</strong>
        <small>{{ error.layer }} · {{ error.code }} · {{ error.recovery }}</small>
      </section>
      <p v-if="notice" class="vault-notice" aria-live="polite">{{ notice }}</p>

      <button
        v-if="canCancel"
        class="cancel"
        type="button"
        :disabled="busy"
        @click="emit('cancel')"
      >取消并返回</button>
    </section>
  </main>
</template>

<style scoped>
.vault-gate {
  --canvas: #eceae4;
  --paper: #fffefa;
  --ink: #1e2523;
  --muted: #646b68;
  --accent: #2e5d57;
  --rule: #c8c9c2;
  --danger: #a33e3e;
  display: grid;
  min-height: 100vh;
  padding: clamp(18px, 5vw, 64px);
  place-items: center;
  color: var(--ink);
  background: var(--canvas);
}

.vault-panel {
  width: min(760px, 100%);
  border: 1px solid var(--rule);
  border-top: 4px solid var(--accent);
  padding: clamp(24px, 5vw, 52px);
  background: var(--paper);
}

.vault-eyebrow,
.preview-kind {
  margin: 0;
  color: var(--muted);
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

h1,
h2 {
  font-family: Georgia, "Times New Roman", serif;
  font-weight: 500;
}

h1 {
  margin: 10px 0;
  font-size: clamp(2.2rem, 6vw, 4rem);
  line-height: 1;
}

label:not(.vault-check) {
  display: grid;
  gap: 8px;
  margin: 26px 0 16px;
  font-weight: 650;
}

input[type="text"] {
  min-width: 0;
  width: 100%;
  border: 1px solid var(--rule);
  border-radius: 0;
  padding: 11px 12px;
  color: var(--ink);
  background: #fff;
}

button {
  border: 1px solid var(--ink);
  border-radius: 0;
  padding: 9px 13px;
  color: var(--ink);
  background: var(--paper);
  cursor: pointer;
}

button:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

button.primary {
  color: var(--paper);
  background: var(--accent);
}

button.danger {
  color: var(--paper);
  background: var(--danger);
}

.vault-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 9px;
}

.vault-preview,
.migration-summary,
.migration-result {
  display: grid;
  gap: 14px;
  margin-top: 28px;
}

code {
  display: block;
  overflow-wrap: anywhere;
  color: var(--muted);
  white-space: pre-wrap;
}

.vault-check {
  display: flex;
  align-items: start;
  gap: 10px;
  margin: 12px 0;
}

.migration-summary dl {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.migration-summary dl div {
  border: 1px solid var(--rule);
  padding: 12px;
}

.migration-summary dt {
  color: var(--muted);
}

.migration-summary dd {
  margin: 4px 0 0;
  font-size: 1.4rem;
}

.migration-issues,
.vault-error {
  border: 1px solid var(--danger);
  padding: 14px;
  background: #fff7f4;
}

.migration-issues li {
  margin-top: 8px;
}

.migration-issues span,
.vault-error small {
  display: block;
  margin-top: 4px;
  color: var(--muted);
}

.vault-error {
  display: grid;
  gap: 5px;
  margin-top: 18px;
}

.vault-notice {
  color: var(--accent);
}

.cancel {
  margin-top: 24px;
}

@media (max-width: 560px) {
  .vault-gate {
    padding: 12px;
  }

  .vault-panel {
    padding: 24px 18px;
  }

  .migration-summary dl {
    grid-template-columns: 1fr;
  }
}
</style>

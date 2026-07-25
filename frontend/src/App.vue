<script setup>
import { onMounted, onUnmounted, ref } from "vue";

import { getRuntimeStatus, restartSidecar } from "./bridge.js";

const status = ref({ state: "starting" });
const restarting = ref(false);
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
  } catch (error) {
    status.value = {
      state: "blocked",
      error,
    };
  } finally {
    restarting.value = false;
  }
}

onMounted(refreshStatus);
onUnmounted(() => window.clearTimeout(refreshTimer));
</script>

<template>
  <main class="runtime-gate" aria-live="polite">
    <section v-if="status.state === 'ready'" class="runtime-panel">
      <p class="eyebrow">Road v0.4 · CP4</p>
      <h1>Python Core 已连接</h1>
      <p>本地宿主和 JSONL sidecar 握手成功。</p>
      <dl>
        <div>
          <dt>应用</dt>
          <dd>{{ status.app_version }}</dd>
        </div>
        <div>
          <dt>Core</dt>
          <dd>{{ status.core_version }}</dd>
        </div>
      </dl>
    </section>

    <section v-else-if="status.state === 'starting'" class="runtime-panel">
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

import { invoke } from "@tauri-apps/api/core";

export async function bridgeRequest(method, params = {}) {
  const response = await invoke("bridge_request", { method, params });
  if (!response?.ok) {
    throw (
      response?.error ?? {
        code: "operation_failed",
        layer: "tauri_host",
        message: "本地边界返回了无效响应。",
        recovery: "restart_sidecar",
      }
    );
  }
  return response.result;
}

export function getRuntimeStatus() {
  return invoke("runtime_status");
}

export function restartSidecar() {
  return invoke("restart_sidecar");
}

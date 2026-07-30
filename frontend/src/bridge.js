import { invoke, isTauri } from "@tauri-apps/api/core";
import { getCurrentWindow } from "@tauri-apps/api/window";
import { confirm } from "@tauri-apps/plugin-dialog";

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

export function chooseVaultDirectory() {
  return invoke("choose_vault_directory");
}

export function openSystemTarget(action, relativeTarget) {
  return invoke("open_system_target", { action, relativeTarget });
}

export function confirmDiscardChanges() {
  const message = "当前有未保存的更改。要放弃更改并继续吗？";
  if (!isTauri()) {
    return Promise.resolve(window.confirm(message));
  }
  return confirm(message, {
    title: "keikeu",
    kind: "warning",
    okLabel: "放弃更改",
    cancelLabel: "继续编辑",
  });
}

export async function registerWindowCloseGuard(requestDeparture) {
  if (!isTauri()) {
    return () => {};
  }
  const currentWindow = getCurrentWindow();
  return currentWindow.onCloseRequested(async (event) => {
    event.preventDefault();
    if (await requestDeparture()) {
      await currentWindow.destroy();
    }
  });
}

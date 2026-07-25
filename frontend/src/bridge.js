import { invoke } from "@tauri-apps/api/core";

export function getRuntimeStatus() {
  return invoke("runtime_status");
}

export function restartSidecar() {
  return invoke("restart_sidecar");
}

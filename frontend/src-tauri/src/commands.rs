use crate::bridge::{BridgeError, BridgeHandle, RuntimeStatus};
use serde_json::Value;
use tauri::{AppHandle, State};
use tauri_plugin_dialog::DialogExt;
use tauri_plugin_opener::OpenerExt;

#[tauri::command]
pub fn runtime_status(bridge: State<'_, BridgeHandle>) -> RuntimeStatus {
    bridge.status()
}

#[tauri::command]
pub async fn bridge_request(
    method: String,
    params: Value,
    bridge: State<'_, BridgeHandle>,
) -> Result<Value, BridgeError> {
    bridge.request(method, params).await
}

#[tauri::command]
pub async fn restart_sidecar(
    bridge: State<'_, BridgeHandle>,
) -> Result<RuntimeStatus, BridgeError> {
    Ok(bridge.restart().await)
}

#[tauri::command]
pub async fn choose_vault_directory(app: AppHandle) -> Result<Option<String>, BridgeError> {
    tauri::async_runtime::spawn_blocking(move || {
        let selected = app.dialog().file().blocking_pick_folder();
        selected
            .map(|path| {
                path.into_path()
                    .map_err(|_| {
                        BridgeError::host(
                            "validation_failed",
                            "所选目录不是本机文件系统路径。",
                            "choose_directory",
                        )
                    })?
                    .into_os_string()
                    .into_string()
                    .map_err(|_| {
                        BridgeError::host(
                            "validation_failed",
                            "所选目录无法表示为 UTF-8 路径。",
                            "choose_directory",
                        )
                    })
            })
            .transpose()
    })
    .await
    .map_err(|_| {
        BridgeError::host(
            "operation_failed",
            "原生目录选择器未完成。",
            "choose_directory",
        )
    })?
}

#[tauri::command]
pub async fn open_system_target(
    action: String,
    relative_target: String,
    app: AppHandle,
    bridge: State<'_, BridgeHandle>,
) -> Result<(), BridgeError> {
    let path = bridge
        .resolve_target(action.clone(), relative_target)
        .await?;
    tauri::async_runtime::spawn_blocking(move || match action.as_str() {
        "open" => app.opener().open_path(path, None::<&str>),
        "reveal" => app.opener().reveal_item_in_dir(path),
        _ => unreachable!("resolve_target validates action"),
    })
    .await
    .map_err(|_| {
        BridgeError::host(
            "operation_failed",
            "系统 open/reveal worker 未完成。",
            "retry_system_action",
        )
    })?
    .map_err(|_| {
        BridgeError::host(
            "operation_failed",
            "系统无法执行已验证的 open/reveal。",
            "retry_system_action",
        )
    })
}

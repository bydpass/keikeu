mod bridge;
mod commands;

use bridge::BridgeHandle;
use tauri::Manager;

pub fn run() {
    let app = tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_opener::init())
        .setup(|app| {
            app.manage(BridgeHandle::start(app.handle().clone()));
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            commands::runtime_status,
            commands::bridge_request,
            commands::restart_sidecar,
            commands::choose_vault_directory,
            commands::open_system_target,
        ])
        .build(tauri::generate_context!())
        .expect("failed to build keikeu desktop host");

    app.run(|app_handle, event| {
        if matches!(
            event,
            tauri::RunEvent::ExitRequested { .. } | tauri::RunEvent::Exit
        ) {
            app_handle.state::<BridgeHandle>().shutdown();
        }
    });
}

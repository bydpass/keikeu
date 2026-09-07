pub mod paper;

#[cfg(not(target_os = "ios"))]
mod bridge;
#[cfg(not(target_os = "ios"))]
mod commands;

#[cfg(not(target_os = "ios"))]
use bridge::BridgeHandle;
#[cfg(not(target_os = "ios"))]
use tauri::Manager;

#[cfg(not(target_os = "ios"))]
pub fn run() {
    let app = tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_opener::init())
        .setup(|app| {
            // The macOS predefined Quit calls Cocoa terminate directly, bypassing close guards.
            #[cfg(target_os = "macos")]
            {
                use tauri::menu::{Menu, MenuItem, PredefinedMenuItem};
                let menu = Menu::default(app.handle())?;
                let items = menu.items()?;
                let app_menu = items
                    .first()
                    .and_then(|item| item.as_submenu())
                    .ok_or("missing macOS app menu")?;
                let items = app_menu.items()?;
                let quit = items
                    .last()
                    .and_then(|item| item.as_predefined_menuitem())
                    .ok_or("missing macOS Quit item")?;
                let quit_text = PredefinedMenuItem::quit(app.handle(), None)?.text()?;
                if quit.text()? != quit_text {
                    return Err("unexpected macOS Quit item".into());
                }
                app_menu.remove(quit)?;
                app_menu.append(&MenuItem::with_id(
                    app.handle(),
                    "guarded-quit",
                    quit_text,
                    true,
                    Some("Cmd+Q"),
                )?)?;
                app.set_menu(menu)?;
                app.on_menu_event(|handle, event| {
                    if event.id() == "guarded-quit" {
                        if let Some(window) = handle.get_webview_window("main") {
                            if window.close().is_err() {
                                eprintln!("could not request guarded window close");
                            }
                        }
                    }
                });
            }
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

#[cfg(target_os = "ios")]
#[tauri::command]
fn runtime_status() -> serde_json::Value {
    serde_json::json!({
        "state": "blocked",
        "error": {
            "code": "mobile_core_pending",
            "layer": "tauri_host",
            "message": "CP1 移动宿主已接通；Paper Core 尚未启用。",
            "recovery": "wait_for_cp3"
        }
    })
}

#[cfg(target_os = "ios")]
#[tauri::mobile_entry_point]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .invoke_handler(tauri::generate_handler![runtime_status])
        .run(tauri::generate_context!())
        .expect("failed to build CP1 mobile host");
}

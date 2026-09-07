mod host;
pub mod paper;

#[cfg(not(target_os = "ios"))]
mod bridge;
#[cfg(not(target_os = "ios"))]
mod commands;

#[cfg(not(target_os = "ios"))]
use bridge::BridgeHandle;
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
fn runtime_status(state: tauri::State<'_, host::Host>) -> serde_json::Value {
    let response = match state.0.lock() {
        Ok(session) => match session.as_ref() {
            Ok(_) => serde_json::json!({"state":"ready"}),
            Err(e) => {
                serde_json::json!({"state":"blocked","error":{"code":e.code,"layer":"rust_host","message":e.reason,"recovery":"reopen_app"}})
            }
        },
        Err(_) => {
            serde_json::json!({"state":"blocked","error":{"code":"host_unavailable","layer":"rust_host","recovery":"reopen_app"}})
        }
    };
    response
}

#[cfg(target_os = "ios")]
#[tauri::command]
async fn bridge_request(
    method: String,
    params: serde_json::Value,
    app: tauri::AppHandle,
) -> serde_json::Value {
    tauri::async_runtime::spawn_blocking(move || {
        let state = app.state::<host::Host>();
        let result = match state.0.lock() {
            Ok(mut session) => match session.as_mut() {
                Ok(s) => s.request(&method, params),
                Err(e) => Err(e.clone()),
            },
            Err(_) => Err(paper::Error::new("host_unavailable", "restart_to_recover")),
        };
        // Release the storage queue before showing a system panel; background draft writes can proceed.
        let result = result.and_then(|v| match v.get("native_export") {
            Some(request) => {
                let result = host::apple::call(request.clone())?;
                if !matches!(result["state"].as_str(), Some("exported" | "cancelled")) {
                    return Err(paper::Error::new("export_failed", "system_export_failed"));
                }
                Ok(result)
            }
            None => Ok(v),
        });
        host::envelope(result)
    })
    .await
    .unwrap_or_else(|_| {
        host::envelope(Err(paper::Error::new(
            "commit_unknown",
            "worker_result_unknown",
        )))
    })
}

#[cfg(target_os = "ios")]
#[tauri::mobile_entry_point]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .setup(|app| {
            let initialized = (|| -> paper::Result<host::Session> {
                let support = app.path().app_data_dir().map_err(|_| {
                    paper::Error::new("host_unavailable", "app_directory_unavailable")
                })?;
                #[cfg(debug_assertions)]
                host::smoke::run(&support);
                let private = support.join("Recovery");
                let locale = host::apple::call(serde_json::json!({"method":"locale"}))?;
                let session = host::Session::open(
                    &support.join("LocalVault"),
                    &private,
                    locale["locale"].as_str().unwrap_or("en"),
                )?;
                Ok(session)
            })();
            app.manage(host::Host(std::sync::Mutex::new(initialized)));
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![runtime_status, bridge_request])
        .run(tauri::generate_context!())
        .expect("failed to build mobile host");
}

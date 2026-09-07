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
            let initialized = (|| -> paper::Result<host::router::Router> {
                let support = app.path().app_data_dir().map_err(|_| {
                    paper::Error::new("host_unavailable", "app_directory_unavailable")
                })?;
                let locale = host::apple::call(serde_json::json!({"method":"locale"}))?;
                host::router::Router::open(
                    &support,
                    None,
                    locale["locale"].as_str().unwrap_or("en"),
                )
            })();
            #[cfg(debug_assertions)]
            if let Ok(support) = app.path().app_data_dir() {
                host::smoke::cloud_run(&support);
            }
            #[cfg(debug_assertions)]
            let initialized = if std::env::args().any(|arg| arg == "--keikeu-cloud-smoke") {
                Err(paper::Error::new(
                    "host_unavailable",
                    "synthetic_smoke_only",
                ))
            } else {
                initialized
            };
            app.manage(host::Host(std::sync::Mutex::new(initialized)));
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
    host::envelope(match host::dispatch(app, method, params).await {
        Ok(host::Dispatch::Native(value)) => Ok(value),
        Ok(host::Dispatch::Python(_)) => Err(paper::Error::new(
            "unsupported_method",
            "method_unavailable",
        )),
        Err(error) => Err(error),
    })
}

#[cfg(target_os = "ios")]
#[tauri::mobile_entry_point]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .setup(|app| {
            let initialized = (|| -> paper::Result<host::router::Router> {
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
                host::router::Router::open(
                    &support,
                    Some(session),
                    locale["locale"].as_str().unwrap_or("en"),
                )
            })();
            #[cfg(debug_assertions)]
            if let Ok(support) = app.path().app_data_dir() {
                host::smoke::cloud_run(&support);
            }
            #[cfg(debug_assertions)]
            let initialized = if std::env::args().any(|arg| arg == "--keikeu-cloud-smoke") {
                Err(paper::Error::new(
                    "host_unavailable",
                    "synthetic_smoke_only",
                ))
            } else {
                initialized
            };
            app.manage(host::Host(std::sync::Mutex::new(initialized)));
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![runtime_status, bridge_request])
        .run(tauri::generate_context!())
        .expect("failed to build mobile host");
}

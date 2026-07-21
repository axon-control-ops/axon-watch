mod host;
mod runtime;

use host::{evaluate_local_action, local_snapshot};
use runtime::{
    control_plane_url, ensure_deployment_env, is_packaged_runtime, start_sidecars, stop_sidecars,
    xdg_paths, CONTROL_PLANE_PORT,
};
use serde::Serialize;
use tauri::{
    menu::{Menu, MenuItem},
    tray::{MouseButton, MouseButtonState, TrayIconBuilder, TrayIconEvent},
    Manager, RunEvent, WindowEvent,
};
use uuid::Uuid;

#[derive(Clone, Serialize)]
struct DesktopBootstrap {
    runtime: &'static str,
    device_id: String,
    capabilities: DesktopCaps,
    control_plane_url: String,
}

#[derive(Clone, Serialize)]
#[serde(rename_all = "camelCase")]
struct DesktopCaps {
    host_bridge: bool,
    tray: bool,
    notifications: bool,
    open_reveal: bool,
    media_control: bool,
    artifact_index: bool,
    packaged_runtime: bool,
}

fn device_id() -> String {
    std::env::var("AXON_DESKTOP_DEVICE_ID")
        .unwrap_or_else(|_| format!("desktop_{}", Uuid::new_v4()))
}

fn operator_token() -> Option<String> {
    std::env::var("AXON_WATCH_OPERATOR_TOKEN")
        .ok()
        .filter(|value| !value.trim().is_empty() && value != "replace-me")
        .or_else(|| {
            let paths = xdg_paths();
            runtime::operator_token_from_env_file(&paths.deployment_env)
        })
}

async fn wait_for_control_plane(timeout_ms: u64) -> Result<(), String> {
    let url = format!("http://127.0.0.1:{CONTROL_PLANE_PORT}/api/health");
    let client = reqwest::Client::builder()
        .timeout(std::time::Duration::from_secs(2))
        .build()
        .map_err(|e| e.to_string())?;
    let deadline = std::time::Instant::now() + std::time::Duration::from_millis(timeout_ms);
    let mut last_err = String::from("control plane did not become healthy");
    while std::time::Instant::now() < deadline {
        match client.get(&url).send().await {
            Ok(response) if response.status().is_success() => return Ok(()),
            Ok(response) => last_err = format!("health status {}", response.status()),
            Err(err) => last_err = err.to_string(),
        }
        tokio::time::sleep(std::time::Duration::from_millis(250)).await;
    }
    Err(last_err)
}

async fn bootstrap_desktop_session(token: &str) -> Result<(), String> {
    let client = reqwest::Client::new();
    let url = format!("http://127.0.0.1:{CONTROL_PLANE_PORT}/api/desktop/bootstrap");
    let response = client
        .post(url)
        .bearer_auth(token)
        .json(&serde_json::json!({ "operator_token": token }))
        .send()
        .await
        .map_err(|e| e.to_string())?;
    if !response.status().is_success() {
        return Err(format!("desktop bootstrap failed: {}", response.status()));
    }
    Ok(())
}

#[tauri::command]
fn get_desktop_bootstrap(state: tauri::State<'_, DesktopBootstrap>) -> DesktopBootstrap {
    state.inner().clone()
}

#[tauri::command]
fn host_snapshot(state: tauri::State<'_, DesktopBootstrap>) -> serde_json::Value {
    local_snapshot(&state.device_id)
}

#[tauri::command]
fn host_evaluate_action(action: String, path: Option<String>) -> serde_json::Value {
    evaluate_local_action(&action, path.as_deref())
}

#[tauri::command]
async fn host_post_snapshot(
    state: tauri::State<'_, DesktopBootstrap>,
) -> Result<serde_json::Value, String> {
    let snapshot = local_snapshot(&state.device_id);
    let client = reqwest::Client::new();
    let mut request = client
        .post(format!(
            "http://127.0.0.1:{CONTROL_PLANE_PORT}/api/host/bridge/snapshot"
        ))
        .json(&serde_json::json!({
            "device_id": state.device_id,
            "snapshot": snapshot,
            "events": []
        }));
    if let Some(token) = operator_token() {
        request = request.bearer_auth(token);
    }
    let response = request.send().await.map_err(|err| err.to_string())?;
    let status = response.status();
    let body = response
        .json::<serde_json::Value>()
        .await
        .map_err(|err| err.to_string())?;
    if !status.is_success() {
        return Err(format!("control plane rejected snapshot: {status} {body}"));
    }
    Ok(body)
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    // Packaged install is detected from env OR sidecar binaries / FHS layout — not only
    // AXON_DESKTOP_PACKAGED (the .deb Exec line does not set that env var).
    let packaged = is_packaged_runtime();

    let paths = xdg_paths();
    let token = ensure_deployment_env(&paths).unwrap_or_default();
    if packaged {
        if let Err(err) = start_sidecars(&paths) {
            eprintln!("VAXON: sidecar start failed: {err}");
        }
    }

    let bootstrap = DesktopBootstrap {
        runtime: "desktop",
        device_id: device_id(),
        capabilities: DesktopCaps {
            host_bridge: true,
            tray: true,
            notifications: false,
            open_reveal: false,
            media_control: false,
            artifact_index: false,
            packaged_runtime: packaged,
        },
        control_plane_url: control_plane_url(),
    };

    let token_owned = token.clone();
    let packaged_owned = packaged;

    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .manage(bootstrap)
        .invoke_handler(tauri::generate_handler![
            get_desktop_bootstrap,
            host_snapshot,
            host_evaluate_action,
            host_post_snapshot
        ])
        .setup(move |app| {
            let show = MenuItem::with_id(app, "show", "Show VAXON", true, None::<&str>)?;
            let quit = MenuItem::with_id(app, "quit", "Quit", true, None::<&str>)?;
            let menu = Menu::with_items(app, &[&show, &quit])?;
            let _tray = TrayIconBuilder::new()
                .menu(&menu)
                .tooltip("VAXON")
                .on_menu_event(|app, event| match event.id.as_ref() {
                    "quit" => {
                        stop_sidecars();
                        app.exit(0);
                    }
                    "show" => {
                        if let Some(window) = app.get_webview_window("main") {
                            let _ = window.show();
                            let _ = window.set_focus();
                        }
                    }
                    _ => {}
                })
                .on_tray_icon_event(|tray, event| {
                    if let TrayIconEvent::Click {
                        button: MouseButton::Left,
                        button_state: MouseButtonState::Up,
                        ..
                    } = event
                    {
                        let app = tray.app_handle();
                        if let Some(window) = app.get_webview_window("main") {
                            let _ = window.show();
                            let _ = window.set_focus();
                        }
                    }
                })
                .build(app)?;

            let handle = app.handle().clone();
            let token_for_boot = token_owned.clone();
            let navigate_packaged = packaged_owned;
            tauri::async_runtime::spawn(async move {
                if navigate_packaged {
                    if let Err(err) = wait_for_control_plane(45_000).await {
                        eprintln!("VAXON: control plane health wait failed: {err}");
                    } else {
                        if !token_for_boot.is_empty() {
                            if let Err(err) = bootstrap_desktop_session(&token_for_boot).await {
                                eprintln!("VAXON: desktop session bootstrap failed: {err}");
                            }
                        }
                        if let Some(window) = handle.get_webview_window("main") {
                            let target = control_plane_url();
                            let _ = window.eval(&format!("window.location.replace({target:?})"));
                        }
                    }
                }
                if let Some(window) = handle.get_webview_window("main") {
                    let bootstrap = handle.state::<DesktopBootstrap>().inner().clone();
                    let script = format!(
                        "window.__AXON_DESKTOP__ = {};",
                        serde_json::to_string(&bootstrap).unwrap_or_else(|_| "{}".into())
                    );
                    let _ = window.eval(&script);
                }
            });

            Ok(())
        })
        .on_window_event(|window, event| {
            if let WindowEvent::CloseRequested { api, .. } = event {
                api.prevent_close();
                let _ = window.hide();
            }
        })
        .build(tauri::generate_context!())
        .expect("error while building VAXON desktop")
        .run(|_app_handle, event| {
            if let RunEvent::ExitRequested { .. } = event {
                stop_sidecars();
            }
        });
}

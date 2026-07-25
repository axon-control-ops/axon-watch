//! Host sensors and outbound control-plane bridge helpers.

mod policy;

use serde::Serialize;
use serde_json::{json, Value};

use policy::{classify_action, ActionTier};

#[derive(Debug, Clone, Serialize)]
pub struct HostIdentity {
    pub device_id: String,
    pub hostname: String,
    pub platform: String,
    pub user: String,
    pub kind: String,
}

pub fn build_host_identity(device_id: &str) -> HostIdentity {
    HostIdentity {
        device_id: device_id.to_string(),
        hostname: hostname::get()
            .ok()
            .and_then(|value| value.into_string().ok())
            .unwrap_or_else(|| "unknown".into()),
        platform: std::env::consts::OS.to_string(),
        user: whoami::username(),
        kind: "desktop_controller".into(),
    }
}

pub fn local_snapshot(device_id: &str) -> Value {
    let identity = build_host_identity(device_id);
    // Identity-only stub: windows/media/health sensors are not implemented yet.
    json!({
        "device_id": identity.device_id,
        "generated_at": chrono::Utc::now().to_rfc3339_opts(chrono::SecondsFormat::Secs, true),
        "host": {
            "hostname": identity.hostname,
            "platform": identity.platform,
            "platform_release": "",
            "machine": std::env::consts::ARCH,
            "user": identity.user,
        },
        "health": {
            "cpu_percent": null,
            "memory_percent": null,
            "battery_percent": null,
            "on_ac": null
        },
        "media": {
            "playing": false,
            "title": "",
            "artist": "",
            "app": ""
        },
        "windows": [],
        "capabilities": [
            "health.snapshot",
            "bridge.heartbeat"
        ],
        "sensor_status": "identity_stub"
    })
}

pub fn evaluate_local_action(action: &str, path: Option<&str>) -> Value {
    let tier = classify_action(action, path);
    let (allowed, reason, requires_approval) = match tier {
        ActionTier::Auto => (true, "safe_auto", false),
        ActionTier::Confirm => (false, "exact_effect_approval_required", true),
        ActionTier::Deny => (false, "action_denied_by_policy", false),
    };
    json!({
        "allowed": allowed,
        "tier": match tier {
            ActionTier::Auto => "auto",
            ActionTier::Confirm => "confirm",
            ActionTier::Deny => "deny",
        },
        "reason": reason,
        "requires_approval": requires_approval
    })
}

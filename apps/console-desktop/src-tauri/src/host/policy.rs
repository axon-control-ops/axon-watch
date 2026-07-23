//! Narrow host bridge policy mirrored by the control-plane safe-auto tiers.

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ActionTier {
    Auto,
    Confirm,
    Deny,
}

pub fn classify_action(action: &str, path: Option<&str>) -> ActionTier {
    let name = action.trim().to_ascii_lowercase();
    match name.as_str() {
        "file.delete"
        | "shell.execute"
        | "input.keystroke"
        | "camera.capture"
        | "mic.capture"
        | "secrets.read"
        | "home.crawl"
        | "artifact.external_upload" => ActionTier::Deny,
        "clipboard.read"
        | "file.read_content"
        | "screenshot.capture"
        | "file.rename"
        | "file.move"
        | "session.lock"
        | "open.sensitive_path"
        | "settings.change" => ActionTier::Confirm,
        "open.path" | "reveal.path" if path_looks_sensitive(path) => ActionTier::Confirm,
        "health.snapshot" | "window.inventory" | "media.status" | "artifact.metadata"
        | "focus.window" | "open.path" | "reveal.path" | "media.play_pause" | "media.next"
        | "media.previous" | "volume.adjust" | "notification.local" | "bridge.heartbeat" => {
            ActionTier::Auto
        }
        _ => ActionTier::Confirm,
    }
}

fn path_looks_sensitive(path: Option<&str>) -> bool {
    let Some(raw) = path.map(|value| value.to_ascii_lowercase()) else {
        return false;
    };
    [
        "/.ssh/",
        "/.gnupg/",
        "/.aws/",
        "password",
        "secret",
        "credential",
        "keychain",
    ]
    .iter()
    .any(|marker| raw.contains(marker))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn auto_for_safe_open() {
        assert_eq!(
            classify_action("open.path", Some("/home/edp/Documents/a.pdf")),
            ActionTier::Auto
        );
    }

    #[test]
    fn confirm_for_sensitive_open() {
        assert_eq!(
            classify_action("open.path", Some("/home/edp/.ssh/id_rsa")),
            ActionTier::Confirm
        );
    }

    #[test]
    fn deny_for_shell() {
        assert_eq!(classify_action("shell.execute", None), ActionTier::Deny);
    }
}

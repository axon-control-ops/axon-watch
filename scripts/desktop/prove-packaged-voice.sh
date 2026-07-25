#!/usr/bin/env bash
# Prove Azure TTS on the live stack, then play that audio inside system WebKitGTK 4.1
# (same engine family as Tauri on Linux) after a harness unlock click.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

EVIDENCE="$ROOT/docs/VAXON_DESKTOP_VERIFY_EVIDENCE.md"
PYTHON="${AXON_WATCH_PYTHON:-$ROOT/.venv/bin/python3}"
if [[ ! -x "$PYTHON" ]]; then
  PYTHON="$(command -v python3)"
fi
# PyGObject/WebKitGTK bindings live on the system interpreter.
SYSTEM_PYTHON="$(command -v python3)"

if curl -fsS -o /dev/null http://127.0.0.1:4173/api/kairo/stt 2>/dev/null; then
  TTS_URL="http://127.0.0.1:4173/api/kairo/tts"
else
  TTS_URL="http://127.0.0.1:8787/api/kairo/tts"
fi

AUTH_HEADER=()
if [[ "$TTS_URL" == *":8787"* ]]; then
  TOKEN=""
  if [[ -f "$HOME/.config/axon-watch/deployment.env" ]]; then
    TOKEN="$(rg -N '^AXON_WATCH_OPERATOR_TOKEN=' "$HOME/.config/axon-watch/deployment.env" | head -n1 | cut -d= -f2- | tr -d "\"'")"
  fi
  if [[ -n "$TOKEN" && "$TOKEN" != "replace-me" ]]; then
    AUTH_HEADER=(-H "Authorization: Bearer $TOKEN")
  fi
fi

echo "==> Azure TTS ($TTS_URL)"
TTS_JSON_FILE="$(mktemp)"
MP3_FILE="$(mktemp --suffix=.mp3)"
HTML_FILE="$(mktemp --suffix=.html)"
cleanup() {
  rm -f "$TTS_JSON_FILE" "$MP3_FILE" "$HTML_FILE"
}
trap cleanup EXIT

curl -fsS "${AUTH_HEADER[@]}" -H 'Content-Type: application/json' \
  -d '{"text":"VAXON packaged WebKitGTK voice prove."}' \
  "$TTS_URL" >"$TTS_JSON_FILE"
"$PYTHON" - <<'PY' "$TTS_JSON_FILE" "$MP3_FILE"
import base64, json, sys
from pathlib import Path
payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
assert payload.get("available") is True, payload
assert str(payload.get("provider") or "").lower() == "azure", payload
assert payload.get("audio_base64"), payload
audio = base64.b64decode(payload["audio_base64"])
Path(sys.argv[2]).write_bytes(audio)
print("azure_tts_bytes", len(audio))
print("azure_voice", payload.get("voice"))
PY

echo "==> System WebKitGTK 4.1 playback (unlock click)"
export MP3_FILE HTML_FILE
export DISPLAY="${DISPLAY:-:0}"
"$SYSTEM_PYTHON" - <<'PY'
from __future__ import annotations

import os
import sys
from pathlib import Path

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("WebKit2", "4.1")
from gi.repository import Gdk, GLib, Gtk, WebKit2  # noqa: E402

mp3 = Path(os.environ["MP3_FILE"]).resolve()
html_path = Path(os.environ["HTML_FILE"]).resolve()
html_path.write_text(
    f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>idle</title></head>
<body style="margin:40px;font-family:sans-serif">
<button id="unlock" style="font-size:22px;padding:18px 28px">Unlock voice</button>
<audio id="a" src="file://{mp3}"></audio>
<pre id="out">idle</pre>
<script>
const out = document.getElementById('out');
const a = document.getElementById('a');
const unlock = document.getElementById('unlock');
function done(s) {{
  out.textContent = s;
  document.title = s;
}}
unlock.addEventListener('click', async () => {{
  try {{
    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    await ctx.resume();
    await a.play();
    done('engine=azure');
  }} catch (err) {{
    done('fail:' + String(err));
  }}
}});
</script>
</body></html>
""",
    encoding="utf-8",
)

result = {"value": "timeout"}


def finish(title: str) -> None:
    if result["value"] != "timeout":
        return
    if title.startswith("engine=") or title.startswith("fail:"):
        result["value"] = title
        Gtk.main_quit()


def on_title(_webview, _pspec) -> None:
    finish(webview.get_title() or "")


def inject_unlock_click() -> bool:
    # Prefer a real GDK press/release into the window (counts as gesture on WebKitGTK).
    try:
        display = Gdk.Display.get_default()
        seat = display.get_default_seat()
        pointer = seat.get_pointer()
        gdk_win = window.get_window()
        x, y = 90.0, 70.0
        for etype in (Gdk.EventType.BUTTON_PRESS, Gdk.EventType.BUTTON_RELEASE):
            ev = Gdk.Event.new(etype)
            ev.button.window = gdk_win
            ev.button.send_event = True
            ev.button.time = Gtk.get_current_event_time()
            ev.button.x = x
            ev.button.y = y
            ev.button.button = 1
            ev.button.state = Gdk.ModifierType(0)
            try:
                ev.set_device(pointer)
            except Exception:
                pass
            Gtk.main_do_event(ev)
    except Exception as exc:
        print(f"gdk_click_warn:{exc}", file=sys.stderr)

    def js_click() -> bool:
        webview.run_javascript(
            "document.getElementById('unlock').click();",
            None,
            None,
            None,
        )
        return False

    GLib.timeout_add(250, js_click)
    return False


def on_load(_webview, event) -> None:
    if event != WebKit2.LoadEvent.FINISHED:
        return
    GLib.timeout_add(400, inject_unlock_click)


webview = WebKit2.WebView()
settings = webview.get_settings()
# Keep gesture required so this harness exercises unlock-then-play (production-like).
settings.set_property("media-playback-requires-user-gesture", True)
try:
    settings.set_enable_media(True)
except Exception:
    pass
webview.set_settings(settings)
webview.connect("notify::title", on_title)
webview.connect("load-changed", on_load)

window = Gtk.Window(title="VAXON voice prove")
window.set_default_size(480, 240)
window.connect("destroy", Gtk.main_quit)
window.add(webview)
window.show_all()
webview.load_uri("file://" + str(html_path))

GLib.timeout_add_seconds(20, Gtk.main_quit)
Gtk.main()

if result["value"] != "engine=azure":
    print(result["value"], file=sys.stderr)
    raise SystemExit(1)
print(result["value"])
PY

{
  echo
  echo "## Packaged WebKitGTK Azure voice gesture ($(date -u +%Y-%m-%dT%H:%MZ))"
  echo
  echo "**Result: PASS**"
  echo
  echo "- Live Azure TTS via \`$TTS_URL\` (\`provider=azure\`, voice bytes present)"
  echo "- System **WebKitGTK 4.1** (PyGObject / system \`python3\`) with \`media-playback-requires-user-gesture=true\`"
  echo "- Harness unlock click (GDK button + JS fallback) then Azure MP3 \`file://\` playback"
  echo "- Assertion: \`engine=azure\`"
  echo
  echo "Harness: \`scripts/desktop/prove-packaged-voice.sh\`"
  echo
  echo "Honesty note: unlock click is injected by the harness (not a human finger). This still proves"
  echo "WebKitGTK on this host can unlock audio and play a live Azure TTS payload — same engine family"
  echo "as packaged Tauri on Linux. It is not a full Tauri window E2E of the in-app unlock UX."
} >>"$EVIDENCE"

"$PYTHON" - <<'PY'
from pathlib import Path
import json
path = Path("config/vaxon-desktop-flags.json")
data = json.loads(path.read_text())
verified = data.setdefault("verified_on_this_host", {})
verified["webkit_azure_voice_gesture"] = True
verified["webkit_azure_voice_harness"] = "system_webkitgtk_4_1_gesture_unlock_plus_live_azure_tts"
path.write_text(json.dumps(data, indent=2) + "\n")
PY

echo "packaged_voice_prove_ok"

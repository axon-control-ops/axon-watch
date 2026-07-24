"""Workspace agent role catalog and display constants."""

from __future__ import annotations

WORKSPACE_AGENT_STATUSES = (
    "idle",
    "watching",
    "assigned",
    "planning",
    "executing",
    "verifying",
    "blocked",
    "waiting_approval",
    "handoff_ready",
)

EMPLOYEE_SCHEDULES = ("always_on", "continuous", "on_demand")

ROLE_CATALOG: tuple[dict[str, str], ...] = (
    {
        "id": "lead",
        "label": "Lead",
        "summary": "Owns priorities, handoffs, and final review",
        "default_schedule": "on_demand",
    },
    {
        "id": "watcher",
        "label": "Watcher",
        "summary": "Monitors signals and runtime health around the clock",
        "default_schedule": "always_on",
    },
    {
        "id": "frontend",
        "label": "Frontend",
        "summary": "Owns UI/UX surfaces and shell polish",
        "default_schedule": "continuous",
    },
    {
        "id": "backend",
        "label": "Backend",
        "summary": "Owns APIs, control plane, and persistence",
        "default_schedule": "continuous",
    },
    {
        "id": "integrations",
        "label": "Integrations",
        "summary": "Owns connectors and cross-service wiring",
        "default_schedule": "continuous",
    },
    {
        "id": "workspace_agent",
        "label": "General",
        "summary": "General company employee for assigned workspace work",
        "default_schedule": "on_demand",
    },
    {
        "id": "overview_agent",
        "label": "Overview",
        "summary": "Cross-workspace overview and routing",
        "default_schedule": "on_demand",
    },
)

# Fallback display names when a company omits employee.name in config.
# Index 0 stays the legacy Axon-X defaults; other slots diversify template companies.
_DEFAULT_ROLE_NAMES = {
    "lead": "Mira",
    "watcher": "Rowan",
    "frontend": "Jules",
    "backend": "Reed",
    "integrations": "Quinn",
    "workspace_agent": "Alex",
    "overview_agent": "Sage",
}

_ROLE_NAME_BANKS: dict[str, tuple[str, ...]] = {
    "lead": ("Mira", "Nora", "Ellis", "Kai", "Samira", "Theo", "Imani", "Owen"),
    "watcher": ("Rowan", "Cass", "Blair", "Nate", "Sky", "Devon", "Remy", "Ash"),
    "frontend": ("Jules", "Priya", "Vera", "Nico", "Lila", "Omar", "Sable", "Rae"),
    "backend": ("Reed", "Marco", "Hugo", "Ivy", "Zane", "Pia", "Cole", "Mina"),
    "integrations": ("Quinn", "Soren", "Tess", "Ari", "Lane", "Noor", "Drew", "Sol"),
    "workspace_agent": ("Alex", "Jamie", "Casey", "Riley"),
    "overview_agent": ("Sage", "Morgan", "Cameron", "Avery"),
}

_ROLE_VOICE_BANKS: dict[str, tuple[str, ...]] = {
    "lead": (
        "en-GB-SoniaNeural",
        "en-US-AriaNeural",
        "en-AU-NatashaNeural",
        "en-IE-EmilyNeural",
    ),
    "watcher": (
        "en-GB-ThomasNeural",
        "en-US-DavisNeural",
        "en-AU-WilliamNeural",
        "en-IE-ConnorNeural",
    ),
    "frontend": (
        "en-GB-LibbyNeural",
        "en-US-JennyNeural",
        "en-AU-FreyaNeural",
        "en-CA-ClaraNeural",
    ),
    "backend": (
        "en-GB-ElliotNeural",
        "en-US-GuyNeural",
        "en-AU-KenNeural",
        "en-CA-LiamNeural",
    ),
    "integrations": (
        "en-GB-HollieNeural",
        "en-US-SaraNeural",
        "en-AU-TinaNeural",
        "en-CA-HeatherNeural",
    ),
}

_DEFAULT_OWNS = {
    "lead": "priorities, handoffs, and product direction",
    "watcher": "signals, connectors, and runtime health",
    "frontend": "UI/UX, shell, and frontend polish",
    "backend": "APIs, control plane, and persistence",
    "integrations": "connectors and integrated services",
}

_ROLE_BY_ID = {entry["id"]: entry for entry in ROLE_CATALOG}

_SCHEDULE_LABELS = {
    "always_on": "Always on (24/7)",
    "continuous": "Continuous",
    "on_demand": "On demand",
}

_BRAND_CASE = {
    "axon": "Axon",
    "dashpro": "DashPro",
}


def stable_role_persona(workspace_id: str, role: str) -> tuple[str, str | None]:
    """Pick a stable personal name (+ optional Azure voice) for template-staffed companies.

    Named ``companies`` entries in workspace-agents.json still win. This only
    diversifies the staffing-template fallback so TPS etc. are not Mira/Rowan clones.
    """
    cleaned_role = (role or "").strip().lower()
    names = _ROLE_NAME_BANKS.get(cleaned_role) or (_DEFAULT_ROLE_NAMES.get(cleaned_role, "Alex"),)
    key = f"{(workspace_id or '').strip().lower()}|{cleaned_role}"
    index = sum(ord(ch) for ch in key) % len(names)
    name = names[index]
    voices = _ROLE_VOICE_BANKS.get(cleaned_role)
    voice = voices[index % len(voices)] if voices else None
    return name, voice


def scoped_default_owns(display_name: str, role: str) -> str:
    base = _DEFAULT_OWNS.get((role or "").strip().lower(), "assigned workspace work")
    title = " ".join(part.capitalize() for part in (display_name or "Workspace").replace("_", " ").split())
    if not title or title.lower() in {"workspace", "demo co", "demo"}:
        return base
    return f"{title}: {base}"


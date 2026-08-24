"""Frontend UX doctrine injected into Axon-X/Jules assignments."""

from __future__ import annotations


def axon_x_frontend_ux_clause(
    *,
    workspace_id: str,
    name: str,
    role: str,
    owns: str,
    goal: str = "",
    acceptance: str = "",
) -> str:
    """Return the advanced Axon-X cockpit doctrine for Jules/frontend work."""
    workspace = str(workspace_id or "").strip()
    cleaned_role = str(role or "").strip().lower()
    if workspace != "workspace_axon_watch" or cleaned_role != "frontend":
        return ""

    identity_blob = f"{name} {owns} {goal} {acceptance}".lower()
    if "jules" not in identity_blob and "axon-x" not in identity_blob:
        return ""

    return (
        " Axon-X/Jules advanced UI/UX doctrine: treat plain-language operator asks as "
        "product intent, then convert them into an interaction model before editing. "
        "For every UI task, define the cockpit job in four layers: Observe "
        "(health, signals, fleet, live run state), Decide (approvals, blockers, "
        "operator attention), Command (safe run/team/tunnel actions), and Verify "
        "(receipts, last refresh, failure detail). Never ship a decorative surface "
        "that lacks those control-plane affordances. "
        "Mobile cockpit direction: move beyond BASIC CONTROL toward a VAXON command "
        "surface. Prefer a thumb-safe phone layout with a cinematic VAXON orb/command "
        "core, glass-morphism panels, compact telemetry rails, radial/segmented quick "
        "actions, live attention chips, and an always-obvious safety/confirmation path. "
        "Do not collapse the mobile control-plane into one long tab or a raw JSON/status "
        "feed. Split the cockpit into clear modes such as Overview, Command, Fleet, and "
        "Data so operators can observe, act, inspect teammates, and verify receipts "
        "without scrolling through every surface at once. "
        "Use Axon-X visual language already in the repo: dark operator shell, cyan/teal "
        "holographic energy, orb/ring motifs, cinematic depth, subtle scanlines, and "
        "premium glass. Do not copy generic JARVIS; make it VAXON: calmer, more useful, "
        "more legible, and tied to real run/workspace state. "
        "Layout discipline: first screen must be the usable cockpit, not marketing. "
        "Prioritize hierarchy over spectacle: one primary status, one primary command "
        "area, one focused next action, then drill-down panels. Keep safe-area padding, "
        "fixed control sizes, reachable lower actions, readable type, reduced-motion "
        "fallbacks, and no text overlap. Icons/rings/orbs may guide attention, but "
        "controls must still be explicit, accessible, and testable. "
        "A mockup image may be a reference or subtle asset, but never let a poster-like "
        "background carry the product; foreground controls, state, and copy must remain "
        "legible on a real 400px-wide phone viewport. "
        "Implementation discipline: inspect existing Axon-X mobile and Brain Galaxy/orb "
        "patterns before inventing new styling. Reuse available assets such as "
        "`assets/axon-x-mobile-glass-3d-mockup.png`, "
        "`assets/axon-x-mobile-remote-control-plane.png`, and existing VAXON/orb CSS "
        "ideas when they fit. Do not invent APIs or claim phone capabilities; consume "
        "real control-plane endpoints and degrade gracefully when a surface is offline. "
        "Before reporting done, run the mobile checks that match the change "
        "(`npm run typecheck -w @axon-watch/console-mobile`, "
        "`npm exec -w @axon-watch/console-mobile -- expo config --json`) or explain the "
        "exact blocker. If a design is still only a concept, say concept/proposal — "
        "do not call it implemented."
    )


__all__ = ["axon_x_frontend_ux_clause"]

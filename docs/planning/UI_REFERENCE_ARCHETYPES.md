# AXON-X UI Reference Archetypes

## Purpose

This document captures external UI/UX references for the AXON-X shell and
translates them into explicit design guidance.

The goal is to achieve an **Iron Man JARVIS-forward command console** that
remains usable as a real IDE and operator control plane.

Canonical visual direction:

- [`UI_VISUAL_DIRECTION.md`](UI_VISUAL_DIRECTION.md)

## Decision Summary

AXON-X should borrow from three families of reference:

1. **JARVIS-style cinematic presence** — primary visual identity
2. **SOC / command-center operational density** — hierarchy and scan order
3. **IDE-grade workbench clarity** — editor/terminal ergonomics

The right blend is:

- **JARVIS-forward shell chrome** across the whole product
- operational hierarchy in the shell and alert model
- IDE clarity in the workbench and interaction model

AXON-X should **not** become:

- a full-screen hologram demo with no real work surfaces
- a security-dashboard clone
- a decorative sci-fi skin over weak information architecture
- a literal Iron Man prop that sacrifices run/signal truth

## Reference Examples

### 1. Local fleet-aware HUD

Reference:

- [bluematter/jarvis](https://github.com/bluematter/jarvis)

Useful traits:

- three-column dashboard mentality
- live tool-activity feed
- fleet awareness beyond one repo
- compact voice/presence focal point

Borrow for AXON-X:

- operator mode can use a left-summary / center-workbench / right-activity
  layout
- a compact KAIRO presence widget can live in the dock or topbar
- cross-workspace awareness should feel immediate

Avoid:

- making a center orb the primary control surface in coding mode
- allowing voice presence to displace editor and run controls

### 2. Cinematic JARVIS HUD

Reference:

- [harsh-raj00/my-jarvis](https://github.com/harsh-raj00/my-jarvis)

Useful traits:

- strong boot sequence identity
- clear voice-state feedback
- premium dark aesthetic
- layered glow and holographic accents

Borrow for AXON-X:

- mandatory boot / wake sequence for shell startup
- distinct states for listening, speaking, thinking, and alerting
- glass panels, cyan edge glow, and HUD corner brackets on hero seams
- subtle atmospheric grid/hex background

Avoid:

- permanent 3D particle centerpieces in steady-state workflow
- excessive animation that slows scanning
- neon treatment on every panel

### 3. Tactical operations dashboard

Reference:

- [Dessiidoo/PeaceKeeper](https://github.com/Dessiidoo/PeaceKeeper)

Useful traits:

- persistent tactical header
- dark-mode-first command-center styling
- live alerts panel
- response modals and mission-oriented structure

Borrow for AXON-X:

- persistent high-trust topbar for shell identity, mode, runtime, and watch
  status
- explicit alert and approval lanes
- response flows that feel like guided operator actions, not generic dialogs

Avoid:

- map-first layouts unless AXON-X actually owns spatial data
- military styling that obscures the product's coding/tooling identity

### 4. High-density SOC terminal

Reference:

- [abhishekk-y/ALISS](https://github.com/abhishekk-y/ALISS)
- [RaaHTecH-Org/aura-ops](https://github.com/RaaHTecH-Org/aura-ops)

Useful traits:

- dense dark layout
- clear status bands
- agent roster / process roster mentality
- incident and remediation framing

Borrow for AXON-X:

- a compact runtime strip with strong status hierarchy
- dock summaries that show active runs, approvals, signals, and thread context
- explicit runbooks / next-safe-actions presentation for operator work

Avoid:

- too many simultaneous widgets competing for attention
- security-only language when the product must also support coding workflows

### 5. Holographic CSS techniques

Reference:

- [Building Holographic UI Effects with Pure CSS](https://hegxib.me/blog/holographic-ui-techniques)

Useful traits:

- glass panels with subtle blur
- gradient edge treatments
- restrained iridescent accents
- motion layered through opacity and gradient shifts rather than heavy 3D

Borrow for AXON-X:

- use holographic treatment only for accents, overlays, or special states
- prefer CSS-driven polish over a heavy visual-effects stack
- provide `prefers-reduced-motion` and low-noise fallbacks

Avoid:

- rainbow surfaces behind body text
- holographic treatment on every panel
- decorative motion that does not carry state meaning

## AXON-X Visual Grammar

### Shell Personality

The shell should feel:

- calm under pressure
- precise
- premium
- operator-grade
- code-capable

It should not feel:

- playful
- neon-chaotic
- fake-military
- dashboard-sprawled

### Information Hierarchy

Every major screen should support a three-step scan:

1. **global state**
   shell mode, workspace identity, watch connectivity, active run truth
2. **active exception**
   what needs attention now: signal, approval, degraded state, or blocked run
3. **evidence and action**
   transcript, diff, editor, terminal, preview, or signal detail

This is the command-center rule AXON-X should inherit most strongly.

### KAIRO Presence Model

KAIRO should be visible as a presence, not as a constant centerpiece.

Recommended presence primitives:

- topbar presence chip
- dock voice / attention state
- optional compact orb or pulse indicator
- spoken-alert status strip
- concise briefing card

KAIRO should not require a full-screen HUD to feel alive.

### Motion Rules

Motion must communicate state changes:

- wake / boot
- new interruptive signal
- listening / speaking / thinking
- run transition
- approval arrival

Motion should not be ambient noise. No always-spinning rings in normal
workflow views.

### Color Rules

Use:

- very dark base surfaces
- restrained electric accents
- semantic colors for signal severity and run state
- enough contrast for 24/7 low-light usage

Avoid:

- making semantic severity indistinguishable from decorative glow
- high-saturation accents on every element

## Concrete UI Guidance For AXON-X

### Operator Mode

Operator mode should feel closest to a command center:

- left side for workspace/system overview
- center for active evidence and current work surface
- right dock for agent, approvals, signals, and thread context
- topbar and status bar always reinforce canonical truth

### IDE Mode

IDE mode should feel closest to a premium coding environment:

- editor dominates center workbench
- terminal and preview remain nearby
- agent dock stays persistent
- operator truth compresses rather than disappears

### Shared Truth

Both modes must show the same:

- run phase
- watch connectivity
- approval state
- signal counts
- current workspace identity

Only emphasis changes.

## Early UX Plan Amendments

These decisions are now locked in planning and delivery:

1. JARVIS-forward visual direction in [`UI_VISUAL_DIRECTION.md`](UI_VISUAL_DIRECTION.md)
2. design tokens for glass/HUD chrome, cyan accents, and semantic status
3. KAIRO presence primitives before deep voice UI implementation
4. boot/wake sequence in UX-0
5. operator-facing labels replacing dev seam copy
6. operator scan hierarchy before adding more widgets

## Acceptance Criteria

This reference work is being followed when:

- the shell feels operator-grade without losing IDE clarity
- KAIRO presence is visible without becoming a gimmick
- cinematic cues are used as accents, not as information substitutes
- the product remains scannable during long real-world sessions

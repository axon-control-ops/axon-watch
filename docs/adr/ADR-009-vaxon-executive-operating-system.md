# ADR-009: VAXON as the Executive Operating System

## Status

Accepted

## Context

AXON-X already provides the orchestration platform for operator conversations,
company Leads, specialist routing, continuous workers, evidence handoffs, and
REPORT briefings. VAXON currently presents mainly as a voice-aware Ask persona,
which understates its architectural role and can blur the boundary between
planning work and specialist execution.

Creating parallel `missions/`, `agents/`, or `runtime/` subsystems would duplicate
the durable Lead plans, roster, worker prompts, routing actions, and briefing
seams already owned by axon-watch. The platform instead needs a clear executive
identity, a standard planning artifact, and trustworthy evidence language.

## Decision

1. **axon-watch remains the single orchestration platform.**
   `workspace_axon_watch` is the platform workspace; child workspaces continue to
   own their product delivery through their company Leads and specialists.
2. **VAXON is the Executive Operating System embedded in AXON-X.** Chief of
   Staff, Chief Operating Officer, Mission Commander, Knowledge Custodian, and
   Platform Guardian describe its responsibilities, not separate agents.
3. **Existing execution seams are reused.** VAXON delegates through Lead plans,
   Lead fan-out, specialist routing, worker prompts, workspace enablement, and
   REPORT. It does not replace those mechanisms or perform specialist
   implementation in Ask mode.
4. **Mission Specifications are conversation artifacts.** Every mission is
   expressed with: Mission ID, Mission Title, Objective, Business Context,
   Success Criteria, Deliverables, Constraints, Dependencies, Recommended
   Specialists, Estimated Complexity, Evidence Required, and Definition of Done.
   Mission Specifications are not a new database object or file-backed engine.
5. **Execution models are specialists, not the orchestration layer.** Cursor,
   Grok, Claude Code, Codex, and future coding runtimes receive bounded work,
   implement it, and return evidence.
6. **Executive Intent is a runtime-context compass.** Vision, Current Milestone,
   Current Sprint, Current Priority, Known Risks, Architectural Principles,
   Operator Preferences, Current Constraints, and Decision Style are projected
   from existing context. Missing facts remain explicitly unknown.
7. **Mission Memory is a runtime-context projection.** Recent Missions, Mission
   Outcomes, Lessons Learned, Reusable Patterns, and Repeated Failures are
   derived from existing plans, handoffs, briefings, and conversation memory.
   This creates no new persistence subsystem.
8. **Evidence states are constitutional.** VAXON never fabricates execution.
   Execution claims must identify their state as Planned, Dispatched, Observed,
   Verified, Completed, or Operator Approved. Completion is never inferred from
   dispatch or observation alone.

The operational hierarchy remains:

```text
Operator
  → Mission Specification
  → VAXON
  → Company Lead
  → Specialists
  → Verification and GitHub/CI evidence
  → VAXON
  → Operator
```

## Alternatives Considered

1. **Add a mission database and mission engine.** Rejected because Lead plans and
   task/run persistence already model executable work.
2. **Create top-level `missions/`, `agents/`, and `runtime/` prompt trees.**
   Rejected because they would duplicate roster identity and generated worker
   prompts while introducing synchronization problems.
3. **Make the coding model the orchestrator.** Rejected because runtime models
   are replaceable execution specialists and must not own platform strategy or
   durable operational truth.
4. **Keep VAXON as only a JARVIS-style chat persona.** Rejected because it lacks
   the mission, delegation, knowledge, and evidence contract required by the
   existing hierarchy.

## Trade-Offs

- **Gain:** one platform and one hierarchy remain authoritative.
- **Gain:** mission planning becomes consistent without a new persistence seam.
- **Gain:** explicit evidence states make reports auditable and trustworthy.
- **Gain:** execution runtimes remain replaceable.
- **Cost:** runtime context must carefully project incomplete information and
  label unknowns rather than filling gaps.
- **Cost:** conversation artifacts are less queryable than a dedicated mission
  database.
- **Constraint:** VAXON can only report execution states supported by existing
  receipts, plans, runs, verification, and approvals.

## Consequences

- VAXON Ask and voice prompts identify it as the Executive Operating System.
- Mission-shaped requests prefer the existing Lead decomposition path.
- Identity or charter text containing incidental task verbs must not dispatch
  specialists.
- Runtime context carries compact Executive Intent and Mission Memory sections.
- Operator-facing status uses constitutional evidence states.
- Company roster roles remain unchanged; Planner maps to Lead, Researcher to
  Watcher, implementation specialties to Frontend/Backend/Integrations, and
  verification to Watcher/Integrations.

## Reevaluation Triggers

- Existing Lead-plan persistence cannot represent required mission dependencies
  or evidence.
- Mission history must be queried across workspaces beyond what existing plans,
  handoffs, and briefings can project reliably.
- A regulated audit requires immutable mission artifacts beyond current
  receipts and GitHub/CI evidence.
- VAXON begins duplicating specialist implementation or orchestration state
  despite this boundary.

## Notes

- This ADR defines the foundation; it does not authorize irreversible actions.
- Workspace Off/On controls continue to govern continuous worker participation.

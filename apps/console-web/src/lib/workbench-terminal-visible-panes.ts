/**
 * Pane layout for the workbench terminal dock.
 * Explicit Split may show two panes; agent-shell mirroring must not auto-split.
 */

export function resolveMirrorVisibleTerminalSessionIds(agentSessionId: string): string[] {
  return [agentSessionId];
}

export function resolveActiveVisibleTerminalSessionIds(input: {
  visibleSessionIds: string[];
  existingSessionIds: Set<string>;
  activeSessionId: string;
}): string[] {
  let kept = input.visibleSessionIds
    .filter((id) => input.existingSessionIds.has(id))
    .slice(0, 2);

  if (!input.existingSessionIds.has(input.activeSessionId)) {
    return kept;
  }

  if (kept.length === 0) {
    return [input.activeSessionId];
  }

  if (!kept.includes(input.activeSessionId)) {
    // Already split: swap the inactive pane. Single pane: replace in place (no auto-split).
    if (kept.length > 1) {
      return [kept[0]!, input.activeSessionId];
    }
    return [input.activeSessionId];
  }

  return kept;
}

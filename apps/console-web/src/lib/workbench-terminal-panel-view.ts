function runPhaseHintParts(runPhase: string | null): string[] {
  if (runPhase === 'executing') {
    return ['Run in progress'];
  }
  if (runPhase === 'review_ready') {
    return ['Review ready'];
  }
  return [];
}

function runPhaseAriaHintParts(runPhase: string | null): string[] {
  if (runPhase === 'executing') {
    return ['run in progress'];
  }
  if (runPhase === 'review_ready') {
    return ['review ready'];
  }
  return [];
}

/** Whether hidden terminal controls should show a live-attention treatment. */
export function workbenchTerminalPanelAlive(runPhase: string | null): boolean {
  return runPhaseHintParts(runPhase).length > 0;
}

/** Tooltip for workbench terminal panel show/hide controls. */
export function workbenchTerminalPanelTitle(
  visible: boolean,
  runPhase: string | null = null,
): string {
  if (visible) {
    return 'Hide terminal panel (Ctrl/Cmd+J)';
  }

  return ['Show terminal panel (Ctrl/Cmd+J)', ...runPhaseHintParts(runPhase)].join(' · ');
}

/** Accessible name for workbench terminal panel show/hide controls. */
export function workbenchTerminalPanelAriaLabel(
  visible: boolean,
  runPhase: string | null = null,
): string {
  if (visible) {
    return 'Hide terminal panel';
  }

  return ['Show terminal panel', ...runPhaseAriaHintParts(runPhase)].join(', ');
}

/** Short label for operator mission-control terminal chip. */
export function operatorTerminalChipLabel(visible: boolean): string {
  return visible ? 'Terminal open' : 'Open terminal · Ctrl/Cmd+J';
}

/** Action label for the mission-control terminal dock footer CTA. */
export function operatorTerminalDockActionLabel(visible: boolean): string {
  return visible ? 'Hide' : 'Show · Ctrl/Cmd+J';
}

/** Tooltip for the IDE activity-bar terminal button. */
export function ideActivityBarTerminalTitle(
  visible: boolean,
  runPhase: string | null = null,
): string {
  const label = 'Terminal (Ctrl/Cmd+J)';
  if (visible) {
    return `${label} · Click to collapse`;
  }

  return [label, ...runPhaseHintParts(runPhase)].join(' · ');
}

/** Accessible name for the IDE activity-bar terminal button. */
export function ideActivityBarTerminalAriaLabel(
  visible: boolean,
  runPhase: string | null = null,
): string {
  const parts = [visible ? 'Collapse terminal panel' : 'Expand terminal panel'];
  if (!visible) {
    parts.push(...runPhaseAriaHintParts(runPhase));
  }
  return parts.join(', ');
}

/** Tooltip for the collapsed workbench terminal reopen strip. */
export function workbenchTerminalReopenTitle(input: {
  runPhase: string | null;
}): string {
  return workbenchTerminalPanelTitle(false, input.runPhase);
}

/** Accessible name for the collapsed workbench terminal reopen strip. */
export function workbenchTerminalReopenAriaLabel(input: {
  runPhase: string | null;
}): string {
  return workbenchTerminalPanelAriaLabel(false, input.runPhase);
}

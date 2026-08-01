export interface AgentDockComposerKeyEvent {
  key: string;
  shiftKey: boolean;
  ctrlKey?: boolean;
  metaKey?: boolean;
  isComposing?: boolean;
}

export function shouldSteerAgentDockComposer(
  event: AgentDockComposerKeyEvent,
): boolean {
  return (
    event.key === 'Enter' &&
    !event.shiftKey &&
    Boolean(event.ctrlKey || event.metaKey) &&
    !Boolean(event.isComposing)
  );
}

/**
 * Cursor Debug Mode: Ctrl/Cmd+Enter continues the reproduce loop (with the
 * operator's reply + attachments) instead of steering a busy agent run.
 */
export function shouldProceedDebugReproduceComposer(
  event: AgentDockComposerKeyEvent,
  debugReproduceActive: boolean,
): boolean {
  return debugReproduceActive && shouldSteerAgentDockComposer(event);
}

export function shouldSubmitAgentDockComposer(
  event: AgentDockComposerKeyEvent,
): boolean {
  if (shouldSteerAgentDockComposer(event)) {
    return false;
  }
  return event.key === 'Enter' && !event.shiftKey && !Boolean(event.isComposing);
}

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

export function shouldSubmitAgentDockComposer(
  event: AgentDockComposerKeyEvent,
): boolean {
  if (shouldSteerAgentDockComposer(event)) {
    return false;
  }
  return event.key === 'Enter' && !event.shiftKey && !Boolean(event.isComposing);
}

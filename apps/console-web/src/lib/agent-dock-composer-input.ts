export interface AgentDockComposerKeyEvent {
  key: string;
  shiftKey: boolean;
  isComposing?: boolean;
}

export function shouldSubmitAgentDockComposer(
  event: AgentDockComposerKeyEvent,
): boolean {
  return event.key === 'Enter' && !event.shiftKey && !Boolean(event.isComposing);
}

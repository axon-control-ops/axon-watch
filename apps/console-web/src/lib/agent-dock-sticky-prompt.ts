/** Last operator prompt to pin above the AgentDock transcript (Cursor-style). */

export type StickyPromptMessage = {
  role?: string | null;
  content?: string | null;
};

export function resolveAgentDockStickyPrompt(input: {
  threadMessages: StickyPromptMessage[];
  activityPrompt?: string | null;
}): string {
  const messages = input.threadMessages ?? [];
  for (let index = messages.length - 1; index >= 0; index -= 1) {
    const message = messages[index];
    if (message?.role === 'operator') {
      const content = String(message.content ?? '').trim();
      if (content) {
        return content;
      }
    }
  }
  return String(input.activityPrompt ?? '').trim();
}

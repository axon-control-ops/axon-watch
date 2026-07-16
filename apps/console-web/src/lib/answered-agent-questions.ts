import type { AgentQuestionOption } from './agent-question-view';

/** Session-local answered ask cards (Cursor-like collapse after Continue). */
const answeredKeys = new Set<string>();

export function questionAnswerKey(messageId: string, prompt: string): string {
  return `${messageId.trim()}::${prompt.trim().slice(0, 160)}`;
}

export function markQuestionAnswered(messageId: string, prompt: string): void {
  const key = questionAnswerKey(messageId, prompt);
  if (key !== '::') {
    answeredKeys.add(key);
  }
}

export function isQuestionMarkedAnswered(messageId: string, prompt: string): boolean {
  return answeredKeys.has(questionAnswerKey(messageId, prompt));
}

/** Match a later user turn to an option from this ask card. */
export function matchQuestionAnswerFromUserText(
  options: AgentQuestionOption[],
  userText: string,
): AgentQuestionOption | null {
  const text = String(userText || '').trim();
  if (!text || options.length === 0) {
    return null;
  }

  const selectedMatch = text.match(/^Selected option\s+(\d+)\s*:\s*(.+)$/im);
  if (selectedMatch) {
    const byId = options.find((option) => option.id === selectedMatch[1]);
    if (byId) {
      return byId;
    }
  }

  const dashMatch = text.match(/^(\d+)\s*[—\-–]\s+(.+)$/);
  if (dashMatch) {
    const byId = options.find((option) => option.id === dashMatch[1]);
    if (byId) {
      return byId;
    }
  }

  if (/^\d+$/.test(text)) {
    return options.find((option) => option.id === text) ?? null;
  }

  const lower = text.toLowerCase();
  return (
    options.find((option) => option.label.trim().toLowerCase() === lower) ??
    options.find((option) => lower.includes(option.label.trim().toLowerCase())) ??
    null
  );
}

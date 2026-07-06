import type { OperatorThreadEntry } from './operator-thread';

export type ThreadSurface = 'operator' | 'ide';

const LANE_B_SYSTEM_RE = /^Lane B \((ask|plan|agent)\)/i;

export function threadSurfaceForLayout(layoutMode: 'operator' | 'ide'): ThreadSurface {
  return layoutMode === 'ide' ? 'ide' : 'operator';
}

function isLaneBSystemMessage(message: OperatorThreadEntry): boolean {
  return message.role === 'system' && LANE_B_SYSTEM_RE.test(message.content);
}

function isCommandSystemMessage(message: OperatorThreadEntry): boolean {
  if (message.role !== 'system' || isLaneBSystemMessage(message)) {
    return false;
  }
  const text = message.content.toLowerCase();
  return (
    text.includes('review_ready') ||
    text.includes('command queued') ||
    text.includes('phase is now') ||
    text.includes('run phase')
  );
}

/** Strip IDE Lane B turns from a legacy mixed operator thread. */
export function filterLegacyOperatorThreadMessages(
  messages: OperatorThreadEntry[],
): OperatorThreadEntry[] {
  const filtered: OperatorThreadEntry[] = [];
  for (let index = 0; index < messages.length; index += 1) {
    const message = messages[index];
    if (!isLaneBSystemMessage(message)) {
      filtered.push(message);
      continue;
    }
    if (filtered.length > 0 && filtered[filtered.length - 1]?.role === 'operator') {
      filtered.pop();
    }
    while (index + 1 < messages.length && messages[index + 1]?.role === 'agent') {
      index += 1;
    }
  }
  return filtered;
}

/** Strip operator command turns and Lane B plumbing from a legacy mixed IDE thread. */
export function filterLegacyIdeThreadMessages(
  messages: OperatorThreadEntry[],
): OperatorThreadEntry[] {
  const filtered: OperatorThreadEntry[] = [];
  for (let index = 0; index < messages.length; index += 1) {
    const message = messages[index];
    // Lane B dispatch receipts ("Lane B (agent) — streaming runtime reply…")
    // are operator-facing plumbing; the IDE transcript shows only the
    // conversational operator/agent turns, like a Cursor thread.
    if (isLaneBSystemMessage(message)) {
      continue;
    }
    if (!isCommandSystemMessage(message)) {
      filtered.push(message);
      continue;
    }
    if (filtered.length > 0 && filtered[filtered.length - 1]?.role === 'operator') {
      filtered.pop();
    }
    while (index + 1 < messages.length && messages[index + 1]?.role === 'agent') {
      index += 1;
    }
  }
  return filtered;
}

export function filterThreadMessagesForSurface(
  messages: OperatorThreadEntry[],
  surface: ThreadSurface,
): OperatorThreadEntry[] {
  return surface === 'operator'
    ? filterLegacyOperatorThreadMessages(messages)
    : filterLegacyIdeThreadMessages(messages);
}

import type { OperatorThreadEntry } from './operator-thread';

export type ThreadSurface = 'operator' | 'ide';

const LANE_B_SYSTEM_RE = /^Lane B \((ask|plan|agent|debug)\)/i;
const FAN_OUT_SYSTEM_RE =
  /^Lead fan-out (assigned task|materialized)/i;

export function threadSurfaceForLayout(layoutMode: 'operator' | 'ide'): ThreadSurface {
  return layoutMode === 'ide' ? 'ide' : 'operator';
}

export function isActiveWorkspaceSurface(options: {
  currentWorkspaceId: string | null | undefined;
  targetWorkspaceId: string;
  currentSurface: ThreadSurface;
  targetSurface: ThreadSurface;
}): boolean {
  return (
    (options.currentWorkspaceId ?? null) === options.targetWorkspaceId &&
    options.currentSurface === options.targetSurface
  );
}

function isLaneBSystemMessage(message: OperatorThreadEntry): boolean {
  return message.role === 'system' && LANE_B_SYSTEM_RE.test(message.content);
}

function isFanOutSystemMessage(message: OperatorThreadEntry): boolean {
  return message.role === 'system' && FAN_OUT_SYSTEM_RE.test(message.content);
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
    // Lane B dispatch receipts and legacy fan-out SYSTEM assigns are plumbing.
    if (isLaneBSystemMessage(message) || isFanOutSystemMessage(message)) {
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

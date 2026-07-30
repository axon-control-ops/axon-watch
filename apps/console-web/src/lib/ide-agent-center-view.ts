import {
  normalizeEditedFilePath,
  parseAgentTranscriptBlocks,
} from './agent-transcript-blocks';
import {
  agentTurnHasConfidenceRating,
  isAgentTurnFailureContent,
} from './kairo-agent-narration';
import { OPERATOR_PERSONA_NAME, personaThreadPrefix } from './operator-persona-name';

export type IdeAgentThreadMessage = {
  message_id: string;
  role: string;
  content: string;
};

export type IdeAgentEditSummary = {
  id: string;
  path: string;
  added: number;
  removed: number;
  diff: string;
  open: boolean;
};

const EDIT_HEADER_RE = /^:::edit\s+(.+?)\s+\+(\d+)\s+-(\d+)\s*$/;

export function resolveActiveIdeAgentMessage(
  messages: readonly IdeAgentThreadMessage[],
  agentStreamActive: boolean,
  agentStreamMessageId: string | null,
): IdeAgentThreadMessage | null {
  if (agentStreamActive && agentStreamMessageId) {
    const streaming = messages.find((message) => message.message_id === agentStreamMessageId);
    if (streaming?.role === 'agent') {
      return streaming;
    }
  }

  for (let index = messages.length - 1; index >= 0; index -= 1) {
    const message = messages[index];
    if (message.role === 'agent' && message.content.trim()) {
      return message;
    }
  }

  return null;
}

/** Prefer IDE agent turns — Mission Control summaries should reflect dock work. */
export function resolveLatestWorkspaceAgentContent(input: {
  agentStreamActive: boolean;
  agentStreamMessageId: string | null;
  ideThreadMessages: readonly IdeAgentThreadMessage[];
  operatorThreadMessages: readonly IdeAgentThreadMessage[];
}): string | null {
  const ideMessage = resolveActiveIdeAgentMessage(
    input.ideThreadMessages,
    input.agentStreamActive,
    input.agentStreamMessageId,
  );
  if (ideMessage?.content.trim()) {
    return ideMessage.content;
  }

  for (let index = input.operatorThreadMessages.length - 1; index >= 0; index -= 1) {
    const message = input.operatorThreadMessages[index];
    if (message.role === 'agent' && message.content.trim()) {
      return message.content;
    }
  }

  return null;
}

/**
 * Extract edit cards from an agent message.
 * Pass `includeDiff: false` for stream-time review strips (paths/counts only).
 */
export function extractIdeAgentEditSummaries(
  content: string,
  messageId: string,
  options?: { includeDiff?: boolean },
): IdeAgentEditSummary[] {
  const includeDiff = options?.includeDiff !== false;
  if (!includeDiff) {
    return extractIdeAgentEditHeadersOnly(content, messageId);
  }

  const edits: IdeAgentEditSummary[] = [];
  parseAgentTranscriptBlocks(content).forEach((segment, index) => {
    if (segment.kind !== 'edit') {
      return;
    }
    edits.push({
      id: `${messageId}:${index}`,
      path: normalizeEditedFilePath(segment.path),
      added: segment.added,
      removed: segment.removed,
      diff: segment.diff,
      open: segment.open,
    });
  });
  return edits;
}

function extractIdeAgentEditHeadersOnly(
  content: string,
  messageId: string,
): IdeAgentEditSummary[] {
  const edits: IdeAgentEditSummary[] = [];
  const lines = content.split('\n');
  let index = 0;
  let editIndex = 0;

  while (index < lines.length) {
    const match = lines[index]?.match(EDIT_HEADER_RE);
    if (!match) {
      index += 1;
      continue;
    }
    let closed = false;
    index += 1;
    while (index < lines.length) {
      if (lines[index]?.trimEnd() === ':::') {
        closed = true;
        index += 1;
        break;
      }
      index += 1;
    }
    edits.push({
      id: `${messageId}:${editIndex}`,
      path: normalizeEditedFilePath(match[1] ?? ''),
      added: Number(match[2] ?? 0),
      removed: Number(match[3] ?? 0),
      diff: '',
      open: !closed,
    });
    editIndex += 1;
  }

  return edits;
}

/** Resolve a single path's diff from thread messages when the strip omitted bodies. */
export function resolveIdeAgentEditDiffFromThread(
  messages: readonly IdeAgentThreadMessage[],
  path: string,
): string {
  const normalized = normalizeEditedFilePath(path);
  for (let messageIndex = messages.length - 1; messageIndex >= 0; messageIndex -= 1) {
    const message = messages[messageIndex];
    if (message?.role !== 'agent') {
      continue;
    }
    for (const edit of extractIdeAgentEditSummaries(message.content, message.message_id, {
      includeDiff: true,
    })) {
      if (edit.path === normalized) {
        return edit.diff;
      }
    }
  }
  return '';
}

/** Collect edit summaries across the thread; later agent messages win on duplicate paths. */
export function collectIdeAgentEditSummariesFromThread(
  messages: readonly IdeAgentThreadMessage[],
  options?: { includeDiff?: boolean },
): IdeAgentEditSummary[] {
  const includeDiff = options?.includeDiff === true;
  const byPath = new Map<string, IdeAgentEditSummary>();
  const order: string[] = [];

  for (const message of messages) {
    if (message.role !== 'agent') {
      continue;
    }
    for (const edit of extractIdeAgentEditSummaries(message.content, message.message_id, {
      includeDiff,
    })) {
      if (!byPath.has(edit.path)) {
        order.push(edit.path);
      }
      byPath.set(edit.path, edit);
    }
  }

  return order
    .map((path) => byPath.get(path))
    .filter((edit): edit is IdeAgentEditSummary => Boolean(edit));
}

/** Latest agent turn failed — do not advertise prior-thread edits as "ready to review". */
export function latestIdeAgentTurnFailed(
  messages: readonly IdeAgentThreadMessage[],
): boolean {
  for (let index = messages.length - 1; index >= 0; index -= 1) {
    const message = messages[index];
    if (message.role === 'agent' && message.content.trim()) {
      return isAgentTurnFailureContent(message.content);
    }
  }
  return false;
}

/**
 * Latest agent turn closed Critical Review with Confidence: N/10.
 * Soft Attention "Try again" must not stay up after a successful close-out.
 */
export function latestIdeAgentTurnHasConfidence(
  messages: readonly IdeAgentThreadMessage[],
): boolean {
  for (let index = messages.length - 1; index >= 0; index -= 1) {
    const message = messages[index];
    if (message.role === 'agent' && message.content.trim()) {
      return agentTurnHasConfidenceRating(message.content);
    }
  }
  return false;
}

export function shouldShowIdeAgentReviewStrip(input: {
  layoutMode: 'operator' | 'ide';
  agentStreamActive: boolean;
  composerAgentBusy: boolean;
  reviewReadyCount: number;
  editedFileCount: number;
  latestAgentTurnFailed?: boolean;
  /** Soft Attention actions (Try again / Explain / Open team) live on this strip. */
  employeeFailureActions?: boolean;
}): boolean {
  if (input.layoutMode !== 'ide') {
    return false;
  }
  if (input.employeeFailureActions) {
    return true;
  }
  if (input.agentStreamActive || input.composerAgentBusy) {
    return true;
  }
  if (input.reviewReadyCount > 0) {
    return true;
  }
  // Failed turns without file edits stay off the strip; file review still wins when
  // the agent produced edits (operator needs Review N files even after a soft fail).
  if (input.latestAgentTurnFailed && input.editedFileCount <= 0) {
    return false;
  }
  return input.editedFileCount > 0;
}

export function parseIdeAgentThreadStatusLabel(
  label: string,
  personaName: string = OPERATOR_PERSONA_NAME,
): { body: string } {
  const trimmed = label.trim();
  const name = personaName.trim() || OPERATOR_PERSONA_NAME;
  const escaped = name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const match = trimmed.match(
    new RegExp(`^(?:${escaped}|${OPERATOR_PERSONA_NAME}|X|KAIRO)\\s*[—-]\\s*(.+)$`, 'i'),
  );
  return { body: match?.[1]?.trim() || trimmed };
}

export function buildIdeAgentThreadStatusLabel(input: {
  activityLabel: string | null | undefined;
  personaName?: string | null;
}): string {
  const persona = input.personaName?.trim() || OPERATOR_PERSONA_NAME;
  const label = String(input.activityLabel ?? 'Agent is working…').trim();
  const escaped = persona.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  if (new RegExp(`^(?:${escaped}|${OPERATOR_PERSONA_NAME})\\b`, 'i').test(label)) {
    return label;
  }
  const body =
    label
      .replace(new RegExp(`^(?:${escaped}|${OPERATOR_PERSONA_NAME}|KAIRO)[:\\s—-]+`, 'i'), '')
      .trim() || 'Agent is working…';
  return personaThreadPrefix(body, persona);
}

export function shouldShowIdeAgentThreadStatusStrip(input: {
  layoutMode: 'operator' | 'ide';
  agentStreamActive: boolean;
  activityLabel: string | null | undefined;
}): boolean {
  if (input.layoutMode !== 'ide' || !input.agentStreamActive) {
    return false;
  }
  return Boolean(String(input.activityLabel ?? '').trim());
}

export function buildIdeAgentReviewComposerLabel(input: {
  agentStreamActive: boolean;
  executionAccess: 'consultative' | 'full';
  editedFileCount: number;
  reviewReadyCount: number;
  expanded: boolean;
  mode?: 'ask' | 'plan' | 'agent' | 'debug';
}): string {
  if (input.agentStreamActive) {
    if (input.editedFileCount > 0) {
      const count = input.editedFileCount;
      const chevron = input.expanded ? '▾' : '▸';
      return `${chevron} ${count === 1 ? '1 file' : `${count} files`}`;
    }
    const mode = input.mode ?? 'agent';
    if (mode === 'ask') {
      return 'Ask — streaming reply…';
    }
    if (mode === 'plan') {
      return 'Plan — streaming outline…';
    }
    if (mode === 'debug' && input.executionAccess === 'full') {
      return 'Debug · Full Access — streaming runtime output…';
    }
    if (mode === 'debug') {
      return 'Debug — streaming runtime output…';
    }
    if (input.executionAccess === 'full') {
      return 'Full Access — streaming runtime output…';
    }
    return 'Agent — streaming runtime output…';
  }
  if (input.editedFileCount > 0) {
    const count = input.editedFileCount;
    const chevron = input.expanded ? '▾' : '▸';
    return `${chevron} ${count === 1 ? '1 file' : `${count} files`}`;
  }
  if (input.reviewReadyCount > 0) {
    return 'Review the agent changes, then apply or complete the run.';
  }
  return 'Agent finished — review file changes in the transcript or editor.';
}

export function buildIdeAgentReviewBar(input: {
  canStop: boolean;
  stopping: boolean;
  canResume?: boolean;
  resuming?: boolean;
  resumeLabel?: string;
  editedFileCount: number;
  reviewReadyCount: number;
  completing: boolean;
}): {
  showStop: boolean;
  showResume: boolean;
  showReview: boolean;
  showApplyAll: boolean;
  stopLabel: string;
  resumeLabel: string;
  reviewLabel: string;
  applyLabel: string;
} {
  const showStop = input.canStop;
  const showResume = Boolean(input.canResume) && !showStop;
  const showReview = input.editedFileCount > 0;
  const showApplyAll = input.reviewReadyCount > 0;

  return {
    showStop,
    showResume,
    showReview,
    showApplyAll,
    stopLabel: input.stopping ? 'Stopping…' : 'Stop',
    resumeLabel: input.resuming
      ? 'Resuming…'
      : (input.resumeLabel ?? 'Resume'),
    reviewLabel:
      input.editedFileCount === 1
        ? 'Review 1 file'
        : `Review ${input.editedFileCount} files`,
    applyLabel: input.completing
      ? 'Applying…'
      : input.reviewReadyCount === 1
        ? 'Apply all'
        : `Apply all (${input.reviewReadyCount})`,
  };
}

import {
  normalizeEditedFilePath,
  parseAgentTranscriptBlocks,
} from './agent-transcript-blocks';

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

export function extractIdeAgentEditSummaries(
  content: string,
  messageId: string,
): IdeAgentEditSummary[] {
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

/** Collect edit summaries across the thread; later agent messages win on duplicate paths. */
export function collectIdeAgentEditSummariesFromThread(
  messages: readonly IdeAgentThreadMessage[],
): IdeAgentEditSummary[] {
  const byPath = new Map<string, IdeAgentEditSummary>();
  const order: string[] = [];

  for (const message of messages) {
    if (message.role !== 'agent') {
      continue;
    }
    for (const edit of extractIdeAgentEditSummaries(message.content, message.message_id)) {
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

export function shouldShowIdeAgentReviewStrip(input: {
  layoutMode: 'operator' | 'ide';
  agentStreamActive: boolean;
  composerAgentBusy: boolean;
  reviewReadyCount: number;
  editedFileCount: number;
}): boolean {
  if (input.layoutMode !== 'ide') {
    return false;
  }
  if (input.agentStreamActive || input.composerAgentBusy) {
    return true;
  }
  if (input.reviewReadyCount > 0) {
    return true;
  }
  return input.editedFileCount > 0;
}

export function buildIdeAgentThreadStatusLabel(input: {
  activityLabel: string | null | undefined;
}): string {
  const label = String(input.activityLabel ?? 'Agent is working…').trim();
  if (/^KAIRO\b/i.test(label)) {
    return label;
  }
  const body = label.replace(/^KAIRO[:\s—-]+/i, '').trim() || 'Agent is working…';
  return `KAIRO — ${body}`;
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
}): string {
  if (input.agentStreamActive) {
    if (input.editedFileCount > 0) {
      const count = input.editedFileCount;
      const chevron = input.expanded ? '▾' : '▸';
      return `${chevron} ${count === 1 ? '1 file' : `${count} files`}`;
    }
    if (input.executionAccess === 'full') {
      return 'Full Access — streaming runtime output…';
    }
    return 'Streaming agent reply…';
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
  editedFileCount: number;
  reviewReadyCount: number;
  completing: boolean;
}): {
  showStop: boolean;
  showReview: boolean;
  showApplyAll: boolean;
  stopLabel: string;
  reviewLabel: string;
  applyLabel: string;
} {
  const showStop = input.canStop;
  const showReview = input.editedFileCount > 0;
  const showApplyAll = input.reviewReadyCount > 0;

  return {
    showStop,
    showReview,
    showApplyAll,
    stopLabel: input.stopping ? 'Stopping…' : 'Stop',
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

import { parseAgentTranscriptBlocks } from './agent-transcript-blocks';

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
      path: segment.path,
      added: segment.added,
      removed: segment.removed,
      diff: segment.diff,
      open: segment.open,
    });
  });
  return edits;
}

export function shouldShowIdeAgentCenterPanel(input: {
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
  return input.reviewReadyCount > 0 && input.editedFileCount > 0;
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

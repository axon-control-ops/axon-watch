/** Compact live lines for the IDE left-rail agent transcript panel. */

import {
  normalizeEditedFilePath,
  parseAgentTranscriptBlocks,
  thinkingPreview,
} from './agent-transcript-blocks';
import { resolveActiveIdeAgentMessage } from './ide-agent-center-view';

export type SidebarTranscriptLineKind =
  | 'thinking'
  | 'tool'
  | 'edit'
  | 'terminal'
  | 'research'
  | 'text'
  | 'status';

export type SidebarTranscriptLine = {
  id: string;
  kind: SidebarTranscriptLineKind;
  text: string;
  live?: boolean;
};

const MAX_SIDEBAR_LINES = 48;
const TEXT_PREVIEW_MAX = 140;

export function buildSidebarAgentTranscriptLines(
  content: string,
  options?: { streaming?: boolean; maxLines?: number },
): SidebarTranscriptLine[] {
  const streaming = Boolean(options?.streaming);
  const maxLines = options?.maxLines ?? MAX_SIDEBAR_LINES;
  const segments = parseAgentTranscriptBlocks(content);
  const lines: SidebarTranscriptLine[] = [];

  segments.forEach((segment, index) => {
    if (segment.kind === 'thinking') {
      const preview = thinkingPreview(segment.text, TEXT_PREVIEW_MAX);
      if (!preview) {
        return;
      }
      lines.push({
        id: `thinking-${index}`,
        kind: 'thinking',
        text: preview,
        live: streaming && segment.open,
      });
      return;
    }
    if (segment.kind === 'tool') {
      lines.push({
        id: `tool-${index}`,
        kind: 'tool',
        text: segment.label.trim() || 'Tool',
      });
      return;
    }
    if (segment.kind === 'edit') {
      const path = normalizeEditedFilePath(segment.path) || 'file';
      lines.push({
        id: `edit-${index}`,
        kind: 'edit',
        text: `${path} +${segment.added} -${segment.removed}`,
        live: streaming && segment.open,
      });
      return;
    }
    if (segment.kind === 'terminal') {
      const command = segment.command.trim() || 'terminal';
      lines.push({
        id: `terminal-${index}`,
        kind: 'terminal',
        text: command.length > TEXT_PREVIEW_MAX
          ? `${command.slice(0, TEXT_PREVIEW_MAX - 1).trimEnd()}…`
          : command,
        live: streaming && segment.open,
      });
      return;
    }
    if (segment.kind === 'research') {
      lines.push({
        id: `research-${index}`,
        kind: 'research',
        text: segment.query.trim() || 'Research',
        live: streaming && segment.open,
      });
      return;
    }
    if (segment.kind === 'text') {
      const flattened = segment.text.replace(/\s+/g, ' ').trim();
      if (!flattened) {
        return;
      }
      lines.push({
        id: `text-${index}`,
        kind: 'text',
        text:
          flattened.length > TEXT_PREVIEW_MAX
            ? `${flattened.slice(0, TEXT_PREVIEW_MAX - 1).trimEnd()}…`
            : flattened,
      });
    }
  });

  if (lines.length === 0 && content.trim()) {
    return [
      {
        id: 'status-0',
        kind: 'status',
        text: streaming ? 'Streaming agent activity…' : 'Agent reply available in dock',
        live: streaming,
      },
    ];
  }

  if (lines.length <= maxLines) {
    return lines;
  }
  return lines.slice(lines.length - maxLines);
}

export function resolveSidebarAgentTranscript(input: {
  messages: readonly { message_id: string; role: string; content: string }[];
  agentStreamActive: boolean;
  agentStreamMessageId: string | null;
}): {
  messageId: string | null;
  streaming: boolean;
  lines: SidebarTranscriptLine[];
  emptyHint: string;
} {
  const active = resolveActiveIdeAgentMessage(
    input.messages,
    input.agentStreamActive,
    input.agentStreamMessageId,
  );
  if (!active?.content.trim()) {
    return {
      messageId: null,
      streaming: false,
      lines: [],
      emptyHint: input.agentStreamActive
        ? 'Waiting for first stream chunk…'
        : 'Select a teammate or open the agent dock for a full transcript',
    };
  }
  const streaming =
    input.agentStreamActive && input.agentStreamMessageId === active.message_id;
  return {
    messageId: active.message_id,
    streaming,
    lines: buildSidebarAgentTranscriptLines(active.content, { streaming }),
    emptyHint: '',
  };
}

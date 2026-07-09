import {
  AGENT_LIVE_LINE_DISPLAY_MAX,
  firstSpeakableAgentLiveBlock,
  flattenLiveLineText,
  isAgentLiveLineTruncated,
  truncateAgentLiveLineForDisplay,
} from './agent-live-line-view';
import { personaThreadPrefix } from './operator-persona-name';

/** X milestone narration for streaming agent turns.
 *
 * Watches the block-annotated agent transcript as it streams and produces
 * short spoken/visual milestones instead of reading raw output aloud.
 */

export type NarrationMilestone = {
  key: string;
  /** Visual / debug label — not spoken verbatim. */
  message: string;
  toolLabel?: string;
  editPath?: string;
  editCount?: number;
};

const THINKING_BLOCK_RE = /:::thinking\n([\s\S]*?)(?:\n:::|$)/;
const THINKING_OPEN_RE = /^:::thinking$/gm;
const TOOL_RE = /^:::tool\s+(.+)$/gm;
const EDIT_RE = /^:::edit\s+(.+?)\s+\+(\d+)\s+-(\d+)\s*$/gm;

function matchAll(content: string, re: RegExp): RegExpMatchArray[] {
  re.lastIndex = 0;
  return [...content.matchAll(re)];
}

/** Live thinking text from an open or closed thinking block. */
export function liveThinkingText(content: string): string {
  const match = content.match(THINKING_BLOCK_RE);
  return match?.[1]?.replace(/\s+/g, ' ').trim() ?? '';
}

export type StreamingActivityView = {
  label: string;
  liveBodyFull: string | null;
  liveBodySpoken: string | null;
  liveBodyTruncated: boolean;
};

/** Status-strip label while the agent transcript streams. */
export function streamingActivityLabel(content: string, fullAccess = false): string {
  return resolveStreamingActivity(content, fullAccess).label;
}

export function resolveStreamingActivity(content: string, fullAccess = false): StreamingActivityView {
  const thinking = liveThinkingText(content);
  if (thinking) {
    const flattened = flattenLiveLineText(thinking);
    const displayBody = truncateAgentLiveLineForDisplay(flattened, AGENT_LIVE_LINE_DISPLAY_MAX);
    return {
      label: personaThreadPrefix(displayBody),
      liveBodyFull: flattened,
      liveBodySpoken: firstSpeakableAgentLiveBlock(flattened),
      liveBodyTruncated: isAgentLiveLineTruncated(flattened, displayBody),
    };
  }

  const tools = matchAll(content, TOOL_RE);
  if (tools.length > 0) {
    const toolLabel = tools[tools.length - 1][1].trim();
    return {
      label: personaThreadPrefix(toolLabel),
      liveBodyFull: toolLabel,
      liveBodySpoken: firstSpeakableAgentLiveBlock(toolLabel),
      liveBodyTruncated: false,
    };
  }

  const fallback = fullAccess ? 'Full Access agent running…' : 'Agent running…';
  return {
    label: personaThreadPrefix(fallback),
    liveBodyFull: null,
    liveBodySpoken: null,
    liveBodyTruncated: false,
  };
}

/** Milestones that newly appeared between the previous and current stream state. */
export function narrationMilestonesForDelta(
  previousContent: string,
  content: string,
): NarrationMilestone[] {
  const milestones: NarrationMilestone[] = [];

  const previousThinking = matchAll(previousContent, THINKING_OPEN_RE).length;
  const thinking = matchAll(content, THINKING_OPEN_RE).length;
  if (thinking > previousThinking && previousThinking === 0) {
    milestones.push({
      key: 'thinking:0',
      message: 'Thinking…',
    });
  }

  const previousTools = matchAll(previousContent, TOOL_RE).length;
  const tools = matchAll(content, TOOL_RE);
  for (let index = previousTools; index < tools.length; index += 1) {
    const label = tools[index][1].trim();
    milestones.push({ key: `tool:${index}`, message: label, toolLabel: label });
  }

  const previousEdits = matchAll(previousContent, EDIT_RE).length;
  const edits = matchAll(content, EDIT_RE);
  for (let index = previousEdits; index < edits.length; index += 1) {
    const [, path, added, removed] = edits[index];
    milestones.push({
      key: `edit:${index}`,
      message: `${path} +${added} -${removed}`,
      editPath: path,
    });
  }

  return milestones;
}

export function narrationForCompletion(content: string): NarrationMilestone {
  const edits = matchAll(content, EDIT_RE);
  if (edits.length === 1) {
    return {
      key: 'done',
      message: 'Done',
      editPath: edits[0][1],
      editCount: 1,
    };
  }
  if (edits.length > 1) {
    return { key: 'done', message: 'Done', editCount: edits.length };
  }
  return { key: 'done', message: 'Done' };
}

function fileBaseName(path: string): string {
  const normalized = path.trim().replace(/\\/g, '/');
  const parts = normalized.split('/');
  return parts[parts.length - 1] || normalized;
}

/** Short status-strip label for the most recent milestone. */
export function narrationActivityLabel(milestone: NarrationMilestone): string {
  return personaThreadPrefix(milestone.message.replace(/\.$/, ''));
}

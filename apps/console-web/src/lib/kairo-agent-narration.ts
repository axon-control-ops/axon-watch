import {
  AGENT_LIVE_LINE_DISPLAY_MAX,
  firstSpeakableAgentLiveBlock,
  isAgentLiveLineTruncated,
  sanitizeAgentThinkingForOperator,
  truncateAgentLiveLineForDisplay,
} from './agent-live-line-view';
import { personaThreadPrefix } from './operator-persona-name';
import { cleanAgentReplyText } from './sanitize-spoken-reply';
import { toolMilestoneSpeakLine } from './kairo-tool-milestone';

const COMPLETION_SUMMARY_MAX = 280;

/** X milestone narration for streaming agent turns.
 *
 * Watches the block-annotated agent transcript as it streams and produces
 * short spoken/visual milestones instead of reading raw output aloud.
 */

export type NarrationMilestone = {
  key: string;
  /** Visual / debug label — not spoken verbatim. */
  message: string;
  /** Read already-sanitized operator-facing copy without model paraphrasing. */
  verbatim?: boolean;
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
export function streamingActivityLabel(
  content: string,
  fullAccess = false,
  personaName?: string | null,
): string {
  return resolveStreamingActivity(content, fullAccess, personaName).label;
}

export function resolveStreamingActivity(
  content: string,
  fullAccess = false,
  personaName?: string | null,
): StreamingActivityView {
  const prefix = (body: string) =>
    personaName?.trim()
      ? personaThreadPrefix(body, personaName.trim())
      : personaThreadPrefix(body);
  const thinking = liveThinkingText(content);
  if (thinking) {
    const sanitized = sanitizeAgentThinkingForOperator(thinking);
    if (sanitized) {
      const displayBody = truncateAgentLiveLineForDisplay(sanitized, AGENT_LIVE_LINE_DISPLAY_MAX);
      return {
        label: prefix(displayBody),
        liveBodyFull: sanitized,
        liveBodySpoken: firstSpeakableAgentLiveBlock(sanitized),
        liveBodyTruncated: isAgentLiveLineTruncated(sanitized, displayBody),
      };
    }
    // Meta-only thinking ("The user is asking…") — do not surface as VAXON copy.
    const fallback = fullAccess ? 'Full Access agent running…' : 'Agent running…';
    return {
      label: prefix(fallback),
      liveBodyFull: null,
      liveBodySpoken: null,
      liveBodyTruncated: false,
    };
  }

  const tools = matchAll(content, TOOL_RE);
  if (tools.length > 0) {
    const toolLabel = tools[tools.length - 1][1].trim();
    return {
      label: prefix(toolLabel),
      liveBodyFull: toolLabel,
      liveBodySpoken: firstSpeakableAgentLiveBlock(toolLabel),
      liveBodyTruncated: false,
    };
  }

  const fallback = fullAccess ? 'Full Access agent running…' : 'Agent running…';
  return {
    label: prefix(fallback),
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
    milestones.push({
      key: `tool:${index}`,
      message: toolMilestoneSpeakLine(label) || label,
      toolLabel: label,
    });
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

/** True when the agent turn ended as a runtime/auth failure, not a successful reply. */
export function isAgentTurnFailureContent(content: string): boolean {
  const text = content.trim();
  if (!text) {
    return false;
  }
  return (
    /Lane B \([^)]+\) cannot start because no CLI runtime is ready/i.test(text) ||
    /cannot start because no CLI runtime is ready/i.test(text) ||
    /\bActionRequiredError\b/i.test(text) ||
    /You're out of usage/i.test(text) ||
    /Codex\/OpenAI API key was rejected/i.test(text)
  );
}

/** First one or two sentences from the final agent reply for end-of-run narration. */
export function spokenCompletionSummary(content: string): string {
  const cleaned = cleanAgentReplyText(content);
  if (!cleaned) {
    return '';
  }
  const flat = cleaned.replace(/\n+/g, ' ').replace(/\s+/g, ' ').trim();
  const sentences = flat.match(/[^.!?]+[.!?]+/g) ?? [];
  if (sentences.length > 0) {
    let summary = (sentences[0] ?? '').trim();
    const second = sentences[1];
    if (summary.length < 120 && second) {
      summary = `${summary} ${second.trim()}`;
    }
    if (summary.length > COMPLETION_SUMMARY_MAX) {
      return `${summary.slice(0, COMPLETION_SUMMARY_MAX - 1).trim()}…`;
    }
    return summary;
  }
  if (flat.length <= COMPLETION_SUMMARY_MAX) {
    return flat;
  }
  return `${flat.slice(0, COMPLETION_SUMMARY_MAX - 1).trim()}…`;
}

export function narrationForCompletion(content: string): NarrationMilestone {
  if (isAgentTurnFailureContent(content)) {
    return { key: 'failed', message: 'Failed' };
  }
  const summary = spokenCompletionSummary(content);
  const hasReproduceMarker = /:::debug-reproduce\b/m.test(content);
  // Reproduce pause: speak a short waiting cue, never the numbered steps.
  if (hasReproduceMarker) {
    return {
      key: 'done',
      message: 'Waiting for you to reproduce the bug.',
      verbatim: true,
    };
  }
  const edits = matchAll(content, EDIT_RE);
  if (edits.length === 1) {
    return {
      key: 'done',
      message: summary || 'Done',
      editPath: edits[0][1],
      editCount: 1,
    };
  }
  if (edits.length > 1) {
    return { key: 'done', message: summary || 'Done', editCount: edits.length };
  }
  return { key: 'done', message: summary || 'Done' };
}

function fileBaseName(path: string): string {
  const normalized = path.trim().replace(/\\/g, '/');
  const parts = normalized.split('/');
  return parts[parts.length - 1] || normalized;
}

/** Short status-strip label for the most recent milestone. */
export function narrationActivityLabel(
  milestone: NarrationMilestone,
  personaName?: string | null,
): string {
  const body = milestone.message.replace(/\.$/, '');
  return personaName?.trim()
    ? personaThreadPrefix(body, personaName.trim())
    : personaThreadPrefix(body);
}

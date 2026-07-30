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
    const sanitized = sanitizeAgentThinkingForOperator(thinking, {
      speakerName: personaName,
    });
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

  // Open thinking alone is not a speakable milestone — live thinking speech waits
  // for a complete sanitized body so we never voice a canned "On it…".

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

const AGENT_CONFIDENCE_LINE_RE = /\bConfidence:\s*(\d{1,2})\s*\/\s*10\b/i;

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

/** Critical Review close-out line — successful shifts end with Confidence: N/10. */
export function agentTurnHasConfidenceRating(content: string): boolean {
  const text = content.trim();
  if (!text || isAgentTurnFailureContent(text)) {
    return false;
  }
  const match = text.match(AGENT_CONFIDENCE_LINE_RE);
  if (!match) {
    return false;
  }
  const score = Number(match[1]);
  return Number.isFinite(score) && score >= 1 && score <= 10;
}

/**
 * Mid-shift / future-tense openers that must not be spoken as the end-of-run
 * bookend after the roster has already flipped to IDLE.
 */
export function isProgressOrIntentSentence(sentence: string): boolean {
  const text = sentence.trim();
  if (!text) {
    return true;
  }
  if (/^\s*(Retrying|Continuing)\b/i.test(text)) {
    return true;
  }
  // Present / future intent: "I am checking…", "I'll publish…", "I will prep…"
  if (
    /^\s*I(?:'m| am|'ll| will)\s+(?:going to |now )?(?:read(?:ing)?|start(?:ing)?|begin(?:ning)?|retry(?:ing)?|check(?:ing)?|look(?:ing)?|scan(?:ning)?|inspect(?:ing)?|open(?:ing)?|review(?:ing)?|draft(?:ing)?|fix(?:ing)?|update(?:ing)?|wire(?:ing)?|produc(?:e|ing)|analyz(?:e|ing)|publish(?:ing)?|prepar(?:e|ing)|run(?:ning)?)\b/i.test(
      text,
    )
  ) {
    return true;
  }
  if (
    /^\s*(Reading|Checking|Looking|Scanning|Inspecting|Opening|Reviewing|Drafting|Analyzing|Working on|Next|Publishing|Preparing)\b/i.test(
      text,
    )
  ) {
    return true;
  }
  if (
    /\bnext,\s+then\b/i.test(text) ||
    /\bthen (?:I will |I'll |fix|produce|update|wire|check|read|publish|prep)\b/i.test(text)
  ) {
    return true;
  }
  return false;
}

/** First one or two sentences from the final agent reply for end-of-run narration. */
export function spokenCompletionSummary(content: string): string {
  const cleaned = cleanAgentReplyText(content);
  if (!cleaned) {
    return '';
  }
  const flat = cleaned.replace(/\n+/g, ' ').replace(/\s+/g, ' ').trim();
  // Prefer the closing confidence line so we do not speak a mid-shift opener
  // ("Retrying my bounded shift now…") after the composer run already stopped.
  const confidence = flat.match(AGENT_CONFIDENCE_LINE_RE);
  if (confidence) {
    const score = confidence[1] ?? '?';
    const withoutConfidence = flat.replace(AGENT_CONFIDENCE_LINE_RE, ' ').replace(/\s+/g, ' ').trim();
    const reportSentences = withoutConfidence.match(/[^.!?]+[.!?]+/g) ?? [];
    const usableReport = reportSentences.filter(
      (sentence) => !isProgressOrIntentSentence(sentence),
    );
    if (usableReport.length > 0) {
      let summary = (usableReport[0] ?? '').trim();
      const second = usableReport[1];
      if (summary.length < 140 && second) {
        summary = `${summary} ${second.trim()}`;
      }
      if (summary.length > COMPLETION_SUMMARY_MAX) {
        summary = `${summary.slice(0, COMPLETION_SUMMARY_MAX - 1).trim()}…`;
      }
      const ended = summary.endsWith('.') || summary.endsWith('…') ? summary : `${summary}.`;
      return `${ended} Confidence ${score} out of 10.`;
    }
    const review = flat.match(/Critical\s+Review[^.!?]{0,160}[.!?]?/i)?.[0]?.trim();
    if (review && review.length >= 24) {
      const clipped =
        review.length > COMPLETION_SUMMARY_MAX
          ? `${review.slice(0, COMPLETION_SUMMARY_MAX - 1).trim()}…`
          : review;
      return clipped.endsWith('.') || clipped.endsWith('…') ? clipped : `${clipped}.`;
    }
    return `Shift complete. Confidence ${score} out of 10.`;
  }
  const sentences = flat.match(/[^.!?]+[.!?]+/g) ?? [];
  const usable = sentences.filter((sentence) => !isProgressOrIntentSentence(sentence));
  // Never fall back to filtered progress openers — that is what makes Priya
  // announce "Reading… next, then fix…" after IDLE.
  if (usable.length > 0) {
    let summary = (usable[0] ?? '').trim();
    const second = usable[1];
    if (summary.length < 120 && second) {
      summary = `${summary} ${second.trim()}`;
    }
    if (summary.length > COMPLETION_SUMMARY_MAX) {
      return `${summary.slice(0, COMPLETION_SUMMARY_MAX - 1).trim()}…`;
    }
    return summary;
  }
  if (sentences.length > 0) {
    return 'Shift complete.';
  }
  if (flat.length <= COMPLETION_SUMMARY_MAX) {
    return isProgressOrIntentSentence(flat) ? 'Shift complete.' : flat;
  }
  if (isProgressOrIntentSentence(flat)) {
    return 'Shift complete.';
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
  // Ask pause: stop mid-run intent speech and cue the operator to the card.
  if (/:::ask\b/m.test(content)) {
    return {
      key: 'done',
      message: 'I need your choice on the ask card.',
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

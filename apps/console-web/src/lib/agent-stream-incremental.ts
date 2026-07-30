import {
  AGENT_LIVE_LINE_DISPLAY_MAX,
  firstSpeakableAgentLiveBlock,
  isAgentLiveLineTruncated,
  sanitizeAgentThinkingForOperator,
  truncateAgentLiveLineForDisplay,
} from './agent-live-line-view';
import type { NarrationMilestone, StreamingActivityView } from './kairo-agent-narration';
import { toolMilestoneSpeakLine } from './kairo-tool-milestone';
import { personaThreadPrefix } from './operator-persona-name';

export type AgentStreamCounts = {
  edit: number;
  terminal: number;
  tool: number;
  research: number;
};

export type AgentStreamIncrementalState = {
  consumeFullContent(content: string): NarrationMilestone[];
  toStreamingActivityView(fullAccess?: boolean): StreamingActivityView;
  toCounts(): AgentStreamCounts;
  takeCompletedThinkingSpeech(): string | null;
  reset(): void;
};

const THINKING_HEADER_RE = /^:::thinking\s*$/;
const TOOL_HEADER_RE = /^:::tool\s+(.+)$/;
const EDIT_HEADER_RE = /^:::edit\s+(.+?)\s+\+(\d+)\s+-(\d+)\s*$/;
const TERMINAL_HEADER_RE = /^:::terminal\s+/;
const RESEARCH_HEADER_RE = /^:::research\s+/;
const DEBUG_REPRODUCE_HEADER_RE = /^:::debug-reproduce\s*$/;
const BLOCK_CLOSE_RE = /^:::\s*$/;

export function createAgentStreamIncrementalState(options?: {
  personaName?: string | null;
}): AgentStreamIncrementalState {
  const personaName = options?.personaName?.trim() || undefined;
  let processedLength = 0;
  let lineBuffer = '';
  let inBlock: 'thinking' | 'other' | null = null;
  let inThinkingBlock = false;
  let thinkingBlockIndex = -1;
  let currentThinkingBody = '';
  const completedThinkingSpeechQueue: string[] = [];
  /** True once the open thinking fence already queued a first speakable sentence. */
  let openThinkingSpeechEmitted = false;
  let thinkingMilestoneEmitted = false;
  let toolCount = 0;
  let editCount = 0;
  let terminalCount = 0;
  let researchCount = 0;
  let lastToolLabel = '';

  function prefixLabel(body: string): string {
    return personaName ? personaThreadPrefix(body, personaName) : personaThreadPrefix(body);
  }

  function reset(): void {
    processedLength = 0;
    lineBuffer = '';
    inBlock = null;
    inThinkingBlock = false;
    thinkingBlockIndex = -1;
    currentThinkingBody = '';
    completedThinkingSpeechQueue.length = 0;
    openThinkingSpeechEmitted = false;
    thinkingMilestoneEmitted = false;
    toolCount = 0;
    editCount = 0;
    terminalCount = 0;
    researchCount = 0;
    lastToolLabel = '';
  }

  function isBlockHeader(line: string): boolean {
    return (
      THINKING_HEADER_RE.test(line.trimEnd()) ||
      TOOL_HEADER_RE.test(line) ||
      EDIT_HEADER_RE.test(line) ||
      TERMINAL_HEADER_RE.test(line) ||
      RESEARCH_HEADER_RE.test(line) ||
      DEBUG_REPRODUCE_HEADER_RE.test(line.trimEnd())
    );
  }

  function queueClosedThinkingSpeech(): void {
    if (openThinkingSpeechEmitted) {
      // Already spoke the first complete sentence while the fence was open —
      // do not re-queue the full block near stream end (plays after Done/ask).
      return;
    }
    const complete = sanitizeAgentThinkingForOperator(currentThinkingBody, {
      speakerName: personaName,
    });
    if (complete) {
      completedThinkingSpeechQueue.push(complete);
    }
  }

  function maybeQueueOpenThinkingSpeech(): void {
    if (openThinkingSpeechEmitted) {
      return;
    }
    const speakable = firstSpeakableAgentLiveBlock(
      sanitizeAgentThinkingForOperator(currentThinkingBody, {
        speakerName: personaName,
      }),
    );
    if (speakable.length < 24) {
      return;
    }
    completedThinkingSpeechQueue.push(speakable);
    openThinkingSpeechEmitted = true;
  }

  function processLine(line: string): NarrationMilestone[] {
    const milestones: NarrationMilestone[] = [];

    if (inBlock === 'thinking' && inThinkingBlock) {
      const trimmedEnd = line.trimEnd();
      if (BLOCK_CLOSE_RE.test(trimmedEnd)) {
        queueClosedThinkingSpeech();
        inBlock = null;
        inThinkingBlock = false;
        currentThinkingBody = '';
        openThinkingSpeechEmitted = false;
        return milestones;
      }
      // Model sometimes glues the close fence onto the last sentence:
      // "…still progressing. :::" — treat as block close, keep the prose.
      if (/(?:^|\s):::\s*$/.test(trimmedEnd)) {
        const withoutClose = trimmedEnd.replace(/\s*:::\s*$/, '');
        if (withoutClose.trim()) {
          if (currentThinkingBody) {
            currentThinkingBody += '\n';
          }
          currentThinkingBody += withoutClose;
        }
        queueClosedThinkingSpeech();
        inBlock = null;
        inThinkingBlock = false;
        currentThinkingBody = '';
        openThinkingSpeechEmitted = false;
        return milestones;
      }
      if (currentThinkingBody) {
        currentThinkingBody += '\n';
      }
      currentThinkingBody += line;
      maybeQueueOpenThinkingSpeech();
      return milestones;
    }

    if (inBlock === 'other') {
      if (BLOCK_CLOSE_RE.test(line.trimEnd())) {
        inBlock = null;
        return milestones;
      }
      if (isBlockHeader(line)) {
        inBlock = null;
        return processLine(line);
      }
      return milestones;
    }

    if (THINKING_HEADER_RE.test(line.trimEnd())) {
      thinkingBlockIndex += 1;
      inThinkingBlock = true;
      inBlock = 'thinking';
      currentThinkingBody = '';
      openThinkingSpeechEmitted = false;
      if (!thinkingMilestoneEmitted) {
        thinkingMilestoneEmitted = true;
        // Do not emit a canned "On it…" speakable milestone — wait for real thinking body.
      }
      return milestones;
    }

    const toolMatch = line.match(TOOL_HEADER_RE);
    if (toolMatch) {
      const label = toolMatch[1].trim();
      const index = toolCount;
      toolCount += 1;
      lastToolLabel = label;
      milestones.push({
        key: `tool:${index}`,
        message: toolMilestoneSpeakLine(label) || label,
        toolLabel: label,
      });
      inBlock = 'other';
      return milestones;
    }

    const editMatch = line.match(EDIT_HEADER_RE);
    if (editMatch) {
      const [, path, added, removed] = editMatch;
      const index = editCount;
      editCount += 1;
      milestones.push({
        key: `edit:${index}`,
        message: `${path} +${added} -${removed}`,
        editPath: path,
      });
      inBlock = 'other';
      return milestones;
    }

    if (TERMINAL_HEADER_RE.test(line)) {
      terminalCount += 1;
      inBlock = 'other';
      return milestones;
    }

    if (RESEARCH_HEADER_RE.test(line)) {
      researchCount += 1;
      inBlock = 'other';
      return milestones;
    }

    if (DEBUG_REPRODUCE_HEADER_RE.test(line.trimEnd())) {
      inBlock = 'other';
      return milestones;
    }

    return milestones;
  }

  function consumeChunk(chunk: string): NarrationMilestone[] {
    const combined = lineBuffer + chunk;
    const parts = combined.split('\n');
    lineBuffer = parts.pop() ?? '';
    const milestones: NarrationMilestone[] = [];
    for (const line of parts) {
      milestones.push(...processLine(line));
    }
    return milestones;
  }

  function consumeFullContent(content: string): NarrationMilestone[] {
    if (content.length < processedLength) {
      reset();
    }
    const delta = content.slice(processedLength);
    processedLength = content.length;
    if (!delta) {
      return [];
    }
    return consumeChunk(delta);
  }

  function liveThinkingTextFromState(): string {
    let body = currentThinkingBody;
    if (inThinkingBlock && lineBuffer) {
      if (body) {
        body += '\n';
      }
      body += lineBuffer;
    }
    const trimmed = body.trim();
    if (!trimmed) {
      return '';
    }
    return trimmed.replace(/\s+/g, ' ').trim();
  }

  function toStreamingActivityView(fullAccess = false): StreamingActivityView {
    const thinking = liveThinkingTextFromState();
    if (thinking) {
      const sanitized = sanitizeAgentThinkingForOperator(thinking, {
        speakerName: personaName,
      });
      if (sanitized) {
        const displayBody = truncateAgentLiveLineForDisplay(sanitized, AGENT_LIVE_LINE_DISPLAY_MAX);
        return {
          label: prefixLabel(displayBody),
          liveBodyFull: sanitized,
          liveBodySpoken: firstSpeakableAgentLiveBlock(sanitized),
          liveBodyTruncated: isAgentLiveLineTruncated(sanitized, displayBody),
        };
      }
      const fallback = fullAccess ? 'Full Access agent running…' : 'Agent running…';
      return {
        label: prefixLabel(fallback),
        liveBodyFull: null,
        liveBodySpoken: null,
        liveBodyTruncated: false,
      };
    }

    if (lastToolLabel) {
      return {
        label: prefixLabel(lastToolLabel),
        liveBodyFull: lastToolLabel,
        liveBodySpoken: firstSpeakableAgentLiveBlock(lastToolLabel),
        liveBodyTruncated: false,
      };
    }

    const fallback = fullAccess ? 'Full Access agent running…' : 'Agent running…';
    return {
      label: prefixLabel(fallback),
      liveBodyFull: null,
      liveBodySpoken: null,
      liveBodyTruncated: false,
    };
  }

  function toCounts(): AgentStreamCounts {
    return {
      edit: editCount,
      terminal: terminalCount,
      tool: toolCount,
      research: researchCount,
    };
  }

  function takeCompletedThinkingSpeech(): string | null {
    return completedThinkingSpeechQueue.shift() ?? null;
  }

  return {
    consumeFullContent,
    takeCompletedThinkingSpeech,
    toStreamingActivityView,
    toCounts,
    reset,
  };
}

import {
  AGENT_LIVE_LINE_DISPLAY_MAX,
  firstSpeakableAgentLiveBlock,
  isAgentLiveLineTruncated,
  sanitizeAgentThinkingForOperator,
  truncateAgentLiveLineForDisplay,
} from './agent-live-line-view';
import type { NarrationMilestone, StreamingActivityView } from './kairo-agent-narration';
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
  reset(): void;
};

const THINKING_HEADER_RE = /^:::thinking\s*$/;
const TOOL_HEADER_RE = /^:::tool\s+(.+)$/;
const EDIT_HEADER_RE = /^:::edit\s+(.+?)\s+\+(\d+)\s+-(\d+)\s*$/;
const TERMINAL_HEADER_RE = /^:::terminal\s+/;
const RESEARCH_HEADER_RE = /^:::research\s+/;
const BLOCK_CLOSE_RE = /^:::\s*$/;

export function createAgentStreamIncrementalState(): AgentStreamIncrementalState {
  let processedLength = 0;
  let lineBuffer = '';
  let inBlock: 'thinking' | 'other' | null = null;
  let inFirstThinking = false;
  let firstThinkingSeen = false;
  let firstThinkingBody = '';
  let thinkingMilestoneEmitted = false;
  let toolCount = 0;
  let editCount = 0;
  let terminalCount = 0;
  let researchCount = 0;
  let lastToolLabel = '';

  function reset(): void {
    processedLength = 0;
    lineBuffer = '';
    inBlock = null;
    inFirstThinking = false;
    firstThinkingSeen = false;
    firstThinkingBody = '';
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
      RESEARCH_HEADER_RE.test(line)
    );
  }

  function processLine(line: string): NarrationMilestone[] {
    const milestones: NarrationMilestone[] = [];

    if (inBlock === 'thinking' && inFirstThinking) {
      if (BLOCK_CLOSE_RE.test(line.trimEnd())) {
        inBlock = null;
        inFirstThinking = false;
        return milestones;
      }
      if (firstThinkingBody) {
        firstThinkingBody += '\n';
      }
      firstThinkingBody += line;
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
      if (!firstThinkingSeen) {
        firstThinkingSeen = true;
        inFirstThinking = true;
        inBlock = 'thinking';
        firstThinkingBody = '';
        if (!thinkingMilestoneEmitted) {
          thinkingMilestoneEmitted = true;
          milestones.push({ key: 'thinking:0', message: 'Thinking…' });
        }
      } else {
        inBlock = 'other';
      }
      return milestones;
    }

    const toolMatch = line.match(TOOL_HEADER_RE);
    if (toolMatch) {
      const label = toolMatch[1].trim();
      const index = toolCount;
      toolCount += 1;
      lastToolLabel = label;
      milestones.push({ key: `tool:${index}`, message: label, toolLabel: label });
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
    let body = firstThinkingBody;
    if (inFirstThinking && lineBuffer) {
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
      const sanitized = sanitizeAgentThinkingForOperator(thinking);
      if (sanitized) {
        const displayBody = truncateAgentLiveLineForDisplay(sanitized, AGENT_LIVE_LINE_DISPLAY_MAX);
        return {
          label: personaThreadPrefix(displayBody),
          liveBodyFull: sanitized,
          liveBodySpoken: firstSpeakableAgentLiveBlock(sanitized),
          liveBodyTruncated: isAgentLiveLineTruncated(sanitized, displayBody),
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

    if (lastToolLabel) {
      return {
        label: personaThreadPrefix(lastToolLabel),
        liveBodyFull: lastToolLabel,
        liveBodySpoken: firstSpeakableAgentLiveBlock(lastToolLabel),
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

  function toCounts(): AgentStreamCounts {
    return {
      edit: editCount,
      terminal: terminalCount,
      tool: toolCount,
      research: researchCount,
    };
  }

  return {
    consumeFullContent,
    toStreamingActivityView,
    toCounts,
    reset,
  };
}

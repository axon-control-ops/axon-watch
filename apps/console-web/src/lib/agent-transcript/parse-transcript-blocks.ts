import { parseAskOptions, resolveAskBlockPrompt, tryParseClarifyingMarkdown } from '../agent-question-view';
import {
  parseLeadFanOutFenceBody,
  tryParseLegacyLeadFanOutText,
} from '../lead-fan-out-card';
import { parseLeadStandupReport } from '../lead-standup-card';
import { sanitizeResearchCardTitle, sanitizeResearchSnippet } from '../research-snippet';import { inferResearchBlockKind, type ResearchBlockKind } from '../research-provider';
import {
  sanitizeTerminalDisplayOutput,
  stripOrphanAnsiFragments,
} from '../terminal-scrollback';
import type { AgentTranscriptSegment, ResearchTranscriptItem } from './types';
import {
  dedupeProseText,
  dedupeTextSegmentsGlobally,
  mergeAdjacentDuplicateTextSegments,
  mergeAdjacentResearchSegments,
} from './prose-dedupe';
import {
  ASK_HEADER_RE,
  DEBUG_REPRODUCE_HEADER_RE,
  EDIT_FAILED_HEADER_RE,
  EDIT_HEADER_RE,
  IMAGE_HEADER_RE,
  LEAD_FAN_OUT_HEADER_RE,
  RESEARCH_HEADER_RE,
  RESEARCH_ITEM_RE,
  RESEARCH_KIND_RE,
  RESEARCH_PROVIDER_RE,
  TERMINAL_HEADER_RE,
  PLAN_HEADER_RE,
  TOOL_HEADER_RE,
} from './transcript-regex';

const TERMINAL_DISPLAY_MAX_CHARS = 16_000;
const TERMINAL_DISPLAY_HEAD_CHARS = 10_000;
const TERMINAL_DISPLAY_TAIL_CHARS = 5_000;

function compactTerminalOutputForDisplay(output: string): string {
  const trimmed = output.replace(/^\n+|\n+$/g, '');
  if (trimmed.length <= TERMINAL_DISPLAY_MAX_CHARS) {
    return trimmed;
  }
  const omitted =
    trimmed.length - TERMINAL_DISPLAY_HEAD_CHARS - TERMINAL_DISPLAY_TAIL_CHARS;
  return [
    trimmed.slice(0, TERMINAL_DISPLAY_HEAD_CHARS).trimEnd(),
    `… [${omitted.toLocaleString('en-US')} characters compacted to keep the IDE responsive; showing output head and tail] …`,
    trimmed.slice(-TERMINAL_DISPLAY_TAIL_CHARS).trimStart(),
  ].join('\n\n');
}

function upgradeClarifyingTextSegments(
  segments: AgentTranscriptSegment[],
): AgentTranscriptSegment[] {
  const next: AgentTranscriptSegment[] = [];
  for (const segment of segments) {
    if (segment.kind !== 'text') {
      next.push(segment);
      continue;
    }
    const leadFanOut = tryParseLegacyLeadFanOutText(segment.text);
    if (leadFanOut) {
      next.push({
        kind: 'lead-fan-out',
        planId: leadFanOut.planId,
        mode: leadFanOut.mode,
        leadName: leadFanOut.leadName,
        title: leadFanOut.title,
        queued: leadFanOut.queued,
        deferred: leadFanOut.deferred,
        assignments: leadFanOut.assignments,
        notes: leadFanOut.notes,
      });
      continue;
    }
    const standup = parseLeadStandupReport(segment.text);
    if (standup) {
      next.push({
        kind: 'lead-standup',
        leadName: standup.leadName,
        title: standup.title,
        intro: standup.intro,
        bodyMarkdown: standup.bodyMarkdown,
        confidence: standup.confidence,
        verificationNotice: standup.verificationNotice,
      });
      continue;
    }
    const question = tryParseClarifyingMarkdown(segment.text);
    if (!question) {
      next.push(segment);
      continue;
    }
    next.push({
      kind: 'question',
      prompt: question.prompt,
      options: question.options,
      open: false,
    });
  }
  return next;
}

export type ParseAgentTranscriptOptions = {
  omitClosedEditDiffs?: boolean;
};

export function parseAgentTranscriptBlocksUncached(
  content: string,
  options?: ParseAgentTranscriptOptions,
): AgentTranscriptSegment[] {
  const omitClosedEditDiffs = options?.omitClosedEditDiffs === true;
  const segments: AgentTranscriptSegment[] = [];
  const lines = content.split('\n');
  let textBuffer: string[] = [];
  let index = 0;

  function flushText(): void {
    let raw = textBuffer.join('\n').replace(/^\n+|\n+$/g, '');
    if (/\[[0-9;?]*[A-Za-z]/.test(raw)) {
      raw = stripOrphanAnsiFragments(raw);
    }
    const text = dedupeProseText(raw);
    if (text.trim()) {
      segments.push({ kind: 'text', text });
    }
    textBuffer = [];
  }

  while (index < lines.length) {
    const line = lines[index];

    if (line.trimEnd() === ':::thinking') {
      flushText();
      const body: string[] = [];
      let closed = false;
      index += 1;
      while (index < lines.length) {
        if (lines[index].trimEnd() === ':::') {
          closed = true;
          index += 1;
          break;
        }
        body.push(lines[index]);
        index += 1;
      }
      segments.push({
        kind: 'thinking',
        text: body.join('\n').replace(/^\n+|\n+$/g, ''),
        open: !closed,
      });
      continue;
    }

    const editMatch = line.match(EDIT_HEADER_RE);
    if (editMatch) {
      flushText();
      let closed = false;
      const bodyStart = index + 1;
      index += 1;
      while (index < lines.length) {
        if (lines[index].trimEnd() === ':::') {
          closed = true;
          break;
        }
        index += 1;
      }
      const bodyEnd = index;
      if (closed) {
        index += 1;
      }
      const keepDiff = !omitClosedEditDiffs || !closed;
      segments.push({
        kind: 'edit',
        path: editMatch[1],
        added: Number(editMatch[2]),
        removed: Number(editMatch[3]),
        diff: keepDiff
          ? lines.slice(bodyStart, bodyEnd).join('\n').replace(/^\n+|\n+$/g, '')
          : '',
        open: !closed,
      });
      continue;
    }

    const editFailedMatch = line.match(EDIT_FAILED_HEADER_RE);
    if (editFailedMatch) {
      flushText();
      const bodyStart = index + 1;
      index += 1;
      let closed = false;
      let bodyEnd = lines.length;
      while (index < lines.length) {
        if (lines[index].trimEnd() === ':::') {
          closed = true;
          bodyEnd = index;
          index += 1;
          break;
        }
        index += 1;
      }
      const reason = lines.slice(bodyStart, bodyEnd).join('\n').trim();
      segments.push({
        kind: 'edit-failed',
        path: editFailedMatch[1].trim(),
        reason: reason || 'Edit was rejected.',
      });
      continue;
    }

    const toolMatch = line.match(TOOL_HEADER_RE);
    if (toolMatch) {
      flushText();
      const label = toolMatch[1].trim();
      const legacyEditFailed = label.match(/^Edit failed\s+(.+)$/i);
      if (legacyEditFailed) {
        segments.push({
          kind: 'edit-failed',
          path: legacyEditFailed[1].trim(),
          reason: 'Edit was rejected (path may be outside write scope or patch did not apply).',
        });
      } else {
        segments.push({ kind: 'tool', label });
      }
      index += 1;
      continue;
    }

    const planMatch = line.match(PLAN_HEADER_RE);
    if (planMatch) {
      flushText();
      const planId = planMatch[1].trim();
      const title = planMatch[2].trim() || 'Untitled plan';
      index += 1;
      if (index < lines.length && lines[index].trimEnd() === ':::') {
        index += 1;
      }
      segments.push({ kind: 'plan', planId, title });
      continue;
    }

    const leadFanOutMatch = line.match(LEAD_FAN_OUT_HEADER_RE);
    if (leadFanOutMatch) {
      flushText();
      const titleHint = (leadFanOutMatch[1] || '').trim() || 'Fan-out';
      const body: string[] = [];
      index += 1;
      while (index < lines.length) {
        if (lines[index].trimEnd() === ':::') {
          index += 1;
          break;
        }
        body.push(lines[index]);
        index += 1;
      }
      const card = parseLeadFanOutFenceBody(body.join('\n'), titleHint);
      if (card) {
        segments.push({
          kind: 'lead-fan-out',
          planId: card.planId,
          mode: card.mode,
          leadName: card.leadName,
          title: card.title,
          queued: card.queued,
          deferred: card.deferred,
          assignments: card.assignments,
          notes: card.notes,
        });
      } else {
        segments.push({ kind: 'text', text: body.join('\n').trim() });
      }
      continue;
    }

    const askMatch = line.match(ASK_HEADER_RE);
    if (askMatch) {
      flushText();
      const headerPrompt = (askMatch[1] || '').trim();
      const body: string[] = [];
      let closed = false;
      index += 1;
      while (index < lines.length) {
        if (lines[index].trimEnd() === ':::') {
          closed = true;
          index += 1;
          break;
        }
        body.push(lines[index]);
        index += 1;
      }
      const options = parseAskOptions(body);
      segments.push({
        kind: 'question',
        prompt: resolveAskBlockPrompt({
          headerPrompt,
          bodyLines: body,
          options,
        }),
        options:
          options.length > 0
            ? options
            : [
                { id: '1', label: 'Yes' },
                { id: '2', label: 'No' },
              ],
        open: !closed,
      });
      continue;
    }

    const researchMatch = line.match(RESEARCH_HEADER_RE);
    if (researchMatch) {
      flushText();
      const items: ResearchTranscriptItem[] = [];
      let closed = false;
      let pendingSnippet: string[] = [];
      let provider = '';
      let kindLabel: ResearchBlockKind | undefined;
      const query = researchMatch[1].trim();
      index += 1;

      function flushSnippet(): void {
        if (items.length === 0 || pendingSnippet.length === 0) {
          pendingSnippet = [];
          return;
        }
        const last = items[items.length - 1];
        const snippet = sanitizeResearchSnippet(pendingSnippet.join('\n').trim());
        last.snippet = snippet;
        last.title = sanitizeResearchCardTitle(last.title, snippet, last.url);
        pendingSnippet = [];
      }

      while (index < lines.length) {
        const current = lines[index];
        if (current.trimEnd() === ':::') {
          closed = true;
          flushSnippet();
          index += 1;
          break;
        }

        const providerMatch = current.match(RESEARCH_PROVIDER_RE);
        if (providerMatch) {
          provider = providerMatch[1].trim();
          index += 1;
          continue;
        }

        const kindMatch = current.match(RESEARCH_KIND_RE);
        if (kindMatch) {
          kindLabel = kindMatch[1].toLowerCase() as ResearchBlockKind;
          index += 1;
          continue;
        }

        const itemMatch = current.match(RESEARCH_ITEM_RE);
        if (itemMatch) {
          flushSnippet();
          items.push({
            title: itemMatch[1].trim(),
            url: itemMatch[2].trim(),
            snippet: '',
          });
          index += 1;
          continue;
        }

        if (items.length > 0) {
          pendingSnippet.push(current);
        }
        index += 1;
      }

      segments.push({
        kind: 'research',
        query,
        items,
        open: !closed,
        provider: provider || undefined,
        kindLabel: kindLabel ?? inferResearchBlockKind(query),
      });
      continue;
    }

    const terminalMatch = line.match(TERMINAL_HEADER_RE);
    if (terminalMatch) {
      flushText();
      const body: string[] = [];
      let closed = false;
      index += 1;
      while (index < lines.length) {
        if (lines[index].trimEnd() === ':::') {
          closed = true;
          index += 1;
          break;
        }
        body.push(lines[index]);
        index += 1;
      }
      const command = terminalMatch[1].trim();
      segments.push({
        kind: 'terminal',
        command,
        output: compactTerminalOutputForDisplay(
          sanitizeTerminalDisplayOutput(body.join('\n'), command),
        ),
        open: !closed,
      });
      continue;
    }

    const imageMatch = line.match(IMAGE_HEADER_RE);
    if (imageMatch) {
      flushText();
      let closed = false;
      index += 1;
      if (index < lines.length && lines[index].trimEnd() === ':::') {
        closed = true;
        index += 1;
      }
      segments.push({
        kind: 'image',
        path: imageMatch[1].trim(),
        open: !closed,
      });
      continue;
    }

    if (DEBUG_REPRODUCE_HEADER_RE.test(line.trimEnd())) {
      flushText();
      const body: string[] = [];
      let closed = false;
      index += 1;
      while (index < lines.length) {
        if (lines[index].trimEnd() === ':::') {
          closed = true;
          index += 1;
          break;
        }
        body.push(lines[index]);
        index += 1;
      }
      const steps = body
        .map((entry) => entry.replace(/^\s*(?:\d+[.)]|[-*])\s*/, '').trim())
        .filter(Boolean);
      segments.push({
        kind: 'debug-reproduce',
        steps: steps.length > 0 ? steps : ['Follow the reproduction steps above, then proceed.'],
        open: !closed,
      });
      continue;
    }

    textBuffer.push(line);
    index += 1;
  }

  flushText();
  return upgradeClarifyingTextSegments(
    dedupeTextSegmentsGlobally(
      mergeAdjacentDuplicateTextSegments(mergeAdjacentResearchSegments(segments)),
    ),
  );
}

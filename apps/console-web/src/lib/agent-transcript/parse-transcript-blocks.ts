import { sanitizeResearchCardTitle, sanitizeResearchSnippet } from '../research-snippet';
import { inferResearchBlockKind, type ResearchBlockKind } from '../research-provider';
import type { AgentTranscriptSegment, ResearchTranscriptItem } from './types';
import {
  dedupeProseText,
  dedupeTextSegmentsGlobally,
  mergeAdjacentDuplicateTextSegments,
  mergeAdjacentResearchSegments,
} from './prose-dedupe';
import {
  DEBUG_REPRODUCE_HEADER_RE,
  EDIT_HEADER_RE,
  IMAGE_HEADER_RE,
  RESEARCH_HEADER_RE,
  RESEARCH_ITEM_RE,
  RESEARCH_KIND_RE,
  RESEARCH_PROVIDER_RE,
  TERMINAL_HEADER_RE,
  TOOL_HEADER_RE,
} from './transcript-regex';

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
    const text = dedupeProseText(textBuffer.join('\n').replace(/^\n+|\n+$/g, ''));
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

    const toolMatch = line.match(TOOL_HEADER_RE);
    if (toolMatch) {
      flushText();
      segments.push({ kind: 'tool', label: toolMatch[1].trim() });
      index += 1;
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
      segments.push({
        kind: 'terminal',
        command: terminalMatch[1].trim(),
        output: body.join('\n').replace(/^\n+|\n+$/g, ''),
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
  return dedupeTextSegmentsGlobally(
    mergeAdjacentDuplicateTextSegments(mergeAdjacentResearchSegments(segments)),
  );
}

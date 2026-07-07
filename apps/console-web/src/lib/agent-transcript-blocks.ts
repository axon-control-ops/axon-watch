/** Parse block-annotated agent transcripts (:::thinking / :::edit / :::tool / :::terminal). */

export type ResearchTranscriptItem = {
  title: string;
  url: string;
  snippet: string;
};
export type AgentTranscriptSegment =
  | { kind: 'text'; text: string }
  | { kind: 'thinking'; text: string; open: boolean }
  | {
      kind: 'edit';
      path: string;
      added: number;
      removed: number;
      diff: string;
      open: boolean;
    }
  | { kind: 'tool'; label: string }
  | { kind: 'research'; query: string; items: ResearchTranscriptItem[]; open: boolean; provider?: string; kindLabel?: ResearchBlockKind }
  | { kind: 'terminal'; command: string; output: string; open: boolean };

import { sanitizeResearchCardTitle, sanitizeResearchSnippet } from './research-snippet';
import { inferResearchBlockKind, type ResearchBlockKind } from './research-provider';

const EDIT_HEADER_RE = /^:::edit\s+(.+?)\s+\+(\d+)\s+-(\d+)\s*$/;
const TOOL_HEADER_RE = /^:::tool\s+(.+)$/;
const RESEARCH_HEADER_RE = /^:::research\s+(.+)$/;
const RESEARCH_ITEM_RE = /^-\s+(.+?)\s+\|\s+(\S+)\s*$/;
const RESEARCH_PROVIDER_RE = /^@provider\s+(.+)$/;
const RESEARCH_KIND_RE = /^@kind\s+(search|fetch)\s*$/i;
const TERMINAL_HEADER_RE = /^:::terminal\s+(.+)$/;

export function agentContentHasTranscriptBlocks(content: string): boolean {
  return /^:::(thinking|edit|tool|terminal|research)\b/m.test(content);
}

export function parseAgentTranscriptBlocks(content: string): AgentTranscriptSegment[] {
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
        kind: 'edit',
        path: editMatch[1],
        added: Number(editMatch[2]),
        removed: Number(editMatch[3]),
        diff: body.join('\n').replace(/^\n+|\n+$/g, ''),
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

    textBuffer.push(line);
    index += 1;
  }

  flushText();
  return mergeAdjacentDuplicateTextSegments(mergeAdjacentResearchSegments(segments));
}

function dedupeProseText(text: string): string {
  if (!text.trim()) {
    return text;
  }

  const dedupedLines: string[] = [];
  for (const line of text.split('\n')) {
    if (line.trim() && dedupedLines.length > 0 && dedupedLines[dedupedLines.length - 1].trim() === line.trim()) {
      continue;
    }
    if (!line.trim() && dedupedLines.length > 0 && !dedupedLines[dedupedLines.length - 1].trim()) {
      continue;
    }
    dedupedLines.push(line);
  }

  const paragraphs = dedupedLines
    .join('\n')
    .split(/\n{2,}/)
    .map((chunk) => chunk.trim())
    .filter(Boolean);
  const uniqueParagraphs: string[] = [];
  for (const paragraph of paragraphs) {
    if (uniqueParagraphs.length > 0 && uniqueParagraphs[uniqueParagraphs.length - 1] === paragraph) {
      continue;
    }
    uniqueParagraphs.push(paragraph);
  }
  return uniqueParagraphs.join('\n\n');
}

function mergeAdjacentDuplicateTextSegments(segments: AgentTranscriptSegment[]): AgentTranscriptSegment[] {
  const merged: AgentTranscriptSegment[] = [];
  for (const segment of segments) {
    const previous = merged[merged.length - 1];
    if (segment.kind === 'text' && previous?.kind === 'text' && previous.text === segment.text) {
      continue;
    }
    merged.push(segment);
  }
  return merged;
}

function normalizeResearchQuery(query: string): string {
  return query.trim().replace(/\s+/g, ' ').toLowerCase();
}

function mergeAdjacentResearchSegments(segments: AgentTranscriptSegment[]): AgentTranscriptSegment[] {
  const merged: AgentTranscriptSegment[] = [];
  for (const segment of segments) {
    const previous = merged[merged.length - 1];
    if (
      segment.kind === 'research' &&
      previous?.kind === 'research' &&
      normalizeResearchQuery(previous.query) === normalizeResearchQuery(segment.query)
    ) {
      merged[merged.length - 1] = {
        kind: 'research',
        query: previous.query,
        items: [...previous.items, ...segment.items],
        open: segment.open,
        provider: previous.provider ?? segment.provider,
        kindLabel: previous.kindLabel ?? segment.kindLabel,
      };
      continue;
    }
    merged.push(segment);
  }
  return merged;
}

export type DiffLineTone = 'add' | 'remove' | 'meta' | 'context';

export function diffLineTone(line: string): DiffLineTone {
  if (line.startsWith('+++') || line.startsWith('---') || line.startsWith('@@')) {
    return 'meta';
  }
  if (line.startsWith('+')) {
    return 'add';
  }
  if (line.startsWith('-')) {
    return 'remove';
  }
  return 'context';
}

export function thinkingPreview(text: string, maxLength = 90): string {
  const flattened = text.replace(/\s+/g, ' ').trim();
  if (flattened.length <= maxLength) {
    return flattened;
  }
  return `${flattened.slice(0, maxLength - 1).trimEnd()}…`;
}

/** Workspace-relative paths mentioned in completed edit blocks. */
export function editedFilePathsFromTranscript(content: string): string[] {
  const paths: string[] = [];
  for (const segment of parseAgentTranscriptBlocks(content)) {
    if (segment.kind !== 'edit' || segment.open) {
      continue;
    }
    const normalized = segment.path.trim().replace(/\\/g, '/');
    if (!normalized || normalized.startsWith('/')) {
      paths.push(fileBaseName(normalized));
      continue;
    }
    paths.push(normalized);
  }
  return [...new Set(paths)];
}

function fileBaseName(path: string): string {
  const parts = path.split('/');
  return parts[parts.length - 1] || path;
}

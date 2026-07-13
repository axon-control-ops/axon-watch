/** Parse block-annotated agent transcripts (:::thinking / :::edit / :::tool / :::terminal). */

import { sanitizeAgentThinkingForOperator } from './agent-live-line-view';

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
  | { kind: 'terminal'; command: string; output: string; open: boolean }
  | { kind: 'image'; path: string; open: boolean };

import { sanitizeResearchCardTitle, sanitizeResearchSnippet } from './research-snippet';
import { inferResearchBlockKind, type ResearchBlockKind } from './research-provider';

const EDIT_HEADER_RE = /^:::edit\s+(.+?)\s+\+(\d+)\s+-(\d+)\s*$/;
const TOOL_HEADER_RE = /^:::tool\s+(.+)$/;
const RESEARCH_HEADER_RE = /^:::research\s+(.+)$/;
const RESEARCH_ITEM_RE = /^-\s+(.+?)\s+\|\s+(\S+)\s*$/;
const RESEARCH_PROVIDER_RE = /^@provider\s+(.+)$/;
const RESEARCH_KIND_RE = /^@kind\s+(search|fetch)\s*$/i;
const TERMINAL_HEADER_RE = /^:::terminal\s+(.+)$/;
const IMAGE_HEADER_RE = /^:::image\s+(.+)$/;

export function agentContentHasTranscriptBlocks(content: string): boolean {
  return /^:::(thinking|edit|tool|terminal|research|image)\b/m.test(content);
}

/** Cheap header counts — safe to run on every stream delta. */
export function countAgentTranscriptHeaders(content: string): {
  edit: number;
  terminal: number;
  tool: number;
  research: number;
} {
  return {
    edit: content.match(/^:::edit\s+/gm)?.length ?? 0,
    terminal: content.match(/^:::terminal\s+/gm)?.length ?? 0,
    tool: content.match(/^:::tool\s+/gm)?.length ?? 0,
    research: content.match(/^:::research\s+/gm)?.length ?? 0,
  };
}

const PARSE_CACHE_LIMIT = 2;
const parseCache = new Map<string, AgentTranscriptSegment[]>();

function rememberParsedSegments(
  content: string,
  segments: AgentTranscriptSegment[],
): AgentTranscriptSegment[] {
  parseCache.set(content, segments);
  if (parseCache.size > PARSE_CACHE_LIMIT) {
    const oldest = parseCache.keys().next().value;
    if (oldest !== undefined) {
      parseCache.delete(oldest);
    }
  }
  return segments;
}

/**
 * Collapse large closed-edit fan-out so the conversation lane does not mount
 * hundreds of diff previews on every stream tick (main-thread freeze).
 */
export function collapseClosedEditSegmentsForDisplay(
  segments: AgentTranscriptSegment[],
  threshold = 12,
): AgentTranscriptSegment[] {
  const closedEditCount = segments.reduce(
    (count, segment) => (segment.kind === 'edit' && !segment.open ? count + 1 : count),
    0,
  );
  if (closedEditCount < threshold) {
    return segments;
  }

  const collapsed: AgentTranscriptSegment[] = [];
  let pendingClosed = 0;

  const flushClosed = (): void => {
    if (pendingClosed <= 0) {
      return;
    }
    collapsed.push({
      kind: 'tool',
      label: pendingClosed === 1 ? 'Updated 1 file' : `Updated ${pendingClosed} files`,
    });
    pendingClosed = 0;
  };

  for (const segment of segments) {
    if (segment.kind === 'edit' && !segment.open) {
      pendingClosed += 1;
      continue;
    }
    flushClosed();
    collapsed.push(segment);
  }
  flushClosed();
  return collapsed;
}

export type ParseAgentTranscriptOptions = {
  /** Skip retaining closed-edit diff bodies (still scans to the closing fence). */
  omitClosedEditDiffs?: boolean;
};

export function prepareAgentTranscriptSegmentsForDisplay(
  content: string,
  options?: { collapseClosedEditsAt?: number },
): AgentTranscriptSegment[] {
  const threshold = options?.collapseClosedEditsAt ?? 12;
  const editCount = countAgentTranscriptHeaders(content).edit;
  // Large edit fan-out: avoid allocating every closed diff body before collapsing.
  const segments =
    editCount >= threshold
      ? parseAgentTranscriptBlocksUncached(content, { omitClosedEditDiffs: true })
      : parseAgentTranscriptBlocks(content);
  return collapseClosedEditSegmentsForDisplay(segments, threshold);
}

export function parseAgentTranscriptBlocks(
  content: string,
  options?: ParseAgentTranscriptOptions,
): AgentTranscriptSegment[] {
  if (options?.omitClosedEditDiffs) {
    return parseAgentTranscriptBlocksUncached(content, options);
  }
  const cached = parseCache.get(content);
  if (cached) {
    return cached;
  }
  return rememberParsedSegments(content, parseAgentTranscriptBlocksUncached(content));
}

function parseAgentTranscriptBlocksUncached(
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

    textBuffer.push(line);
    index += 1;
  }

  flushText();
  return dedupeTextSegmentsGlobally(
    mergeAdjacentDuplicateTextSegments(mergeAdjacentResearchSegments(segments)),
  );
}

function filterSeenParagraphs(text: string, seen: Set<string>): string {
  if (!text.trim()) {
    return text;
  }

  const kept: string[] = [];
  for (const paragraph of text
    .split(/\n{2,}/)
    .map((chunk) => chunk.trim())
    .filter(Boolean)) {
    if (seen.has(paragraph)) {
      continue;
    }
    seen.add(paragraph);
    kept.push(paragraph);
  }
  return kept.join('\n\n');
}

function dedupeTextSegmentsGlobally(segments: AgentTranscriptSegment[]): AgentTranscriptSegment[] {
  const seenParagraphs = new Set<string>();
  const deduped: AgentTranscriptSegment[] = [];

  for (const segment of segments) {
    if (segment.kind !== 'text') {
      deduped.push(segment);
      continue;
    }

    const filtered = filterSeenParagraphs(dedupeProseText(segment.text), seenParagraphs);
    if (!filtered.trim()) {
      continue;
    }

    const previous = deduped[deduped.length - 1];
    if (previous?.kind === 'text' && previous.text === filtered) {
      continue;
    }

    deduped.push({ kind: 'text', text: filtered });
  }

  return deduped;
}

function collapseDuplicatedBody(text: string): string {
  const stripped = text.trim();
  if (!stripped) {
    return text;
  }

  const normalized = stripped.replace(/\r\n/g, '\n');

  if (normalized.length >= 2 && normalized.length % 2 === 0) {
    const half = normalized.length / 2;
    if (normalized.slice(0, half) === normalized.slice(half)) {
      return normalized.slice(0, half);
    }
  }

  const mid = Math.floor(normalized.length / 2);
  const left = normalized.slice(0, mid).trim();
  const right = normalized.slice(mid).trim();
  if (left && left === right) {
    return left;
  }

  const lines = normalized.split('\n');
  if (lines.length >= 2 && lines.length % 2 === 0) {
    const half = lines.length / 2;
    if (lines.slice(0, half).join('\n') === lines.slice(half).join('\n')) {
      return lines.slice(0, half).join('\n');
    }
  }

  const paragraphs = normalized
    .split(/\n{2,}/)
    .map((chunk) => chunk.trim())
    .filter(Boolean);
  if (paragraphs.length >= 2 && paragraphs.length % 2 === 0) {
    const half = paragraphs.length / 2;
    if (paragraphs.slice(0, half).every((paragraph, index) => paragraph === paragraphs[half + index])) {
      return paragraphs.slice(0, half).join('\n\n');
    }
  }

  if (normalized.includes('\n\n')) {
    const [leftPart, rightPart] = normalized.split('\n\n', 2);
    if (leftPart.trim() && leftPart.trim() === rightPart.trim()) {
      return leftPart.trim();
    }
  }

  return text;
}

function dedupeProseText(text: string): string {
  if (!text.trim()) {
    return text;
  }

  text = collapseDuplicatedBody(text);
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
  const sanitized = sanitizeAgentThinkingForOperator(text);
  const flattened = (sanitized || 'Thinking…').replace(/\s+/g, ' ').trim();
  if (flattened.length <= maxLength) {
    return flattened;
  }
  return `${flattened.slice(0, maxLength - 1).trimEnd()}…`;
}

/** Map agent edit paths to workspace-relative paths the file API understands. */
export function normalizeEditedFilePath(path: string): string {
  const normalized = path.trim().replace(/\\/g, '/');
  if (!normalized || normalized.startsWith('/')) {
    return fileBaseName(normalized);
  }
  return normalized;
}

/** Workspace-relative paths mentioned in completed edit blocks. */
export function editedFilePathsFromTranscript(content: string): string[] {
  const paths: string[] = [];
  for (const segment of parseAgentTranscriptBlocks(content)) {
    if (segment.kind !== 'edit' || segment.open) {
      continue;
    }
    paths.push(normalizeEditedFilePath(segment.path));
  }
  return [...new Set(paths)];
}

function fileBaseName(path: string): string {
  const parts = path.split('/');
  return parts[parts.length - 1] || path;
}

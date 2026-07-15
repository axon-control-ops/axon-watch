import type { AgentTranscriptSegment } from './types';

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

export function dedupeTextSegmentsGlobally(segments: AgentTranscriptSegment[]): AgentTranscriptSegment[] {
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

const SUFFIX_ECHO_MIN = 80;
const SUFFIX_ECHO_SEMANTIC_MIN = 60;
const GLUED_SENTENCE_RESTART_RE =
  /(?<=[.!?…])(["'`‘’“”)\]]*)(?=[A-Z"'“‘])/g;
const MARKDOWN_HEADING_RE = /^\*\*[^*\n]+?\*\*\s*$/gm;

function semanticProseKey(text: string): string {
  return text.replace(/\W+/g, '').toLowerCase();
}

function tokenSet(text: string): Set<string> {
  return new Set((text.toLowerCase().match(/[a-z0-9]+/g) ?? []).filter(Boolean));
}

function suffixIsEchoOfPrefix(left: string, right: string): boolean {
  if (right.length < SUFFIX_ECHO_MIN || left.length < SUFFIX_ECHO_MIN) {
    return false;
  }
  const skLeft = semanticProseKey(left);
  const skRight = semanticProseKey(right);
  if (skRight.length < SUFFIX_ECHO_SEMANTIC_MIN || skLeft.length < SUFFIX_ECHO_SEMANTIC_MIN) {
    return false;
  }
  if (skLeft.includes(skRight)) {
    return true;
  }
  // Aggregates sometimes skip a middle section, so the echo is not contiguous.
  if (right.length > left.length + 64) {
    return false;
  }

  const rightTokens = tokenSet(right);
  const leftTokens = tokenSet(left);
  if (rightTokens.size === 0) {
    return false;
  }
  let overlap = 0;
  for (const token of rightTokens) {
    if (leftTokens.has(token)) {
      overlap += 1;
    }
  }
  if (overlap / rightTokens.size < 0.92) {
    return false;
  }

  const restartKey = semanticProseKey(right.slice(0, 160));
  if (restartKey.length >= 40 && skLeft.includes(restartKey)) {
    return true;
  }
  const stem = skRight.slice(
    0,
    Math.max(SUFFIX_ECHO_SEMANTIC_MIN, Math.floor((skRight.length * 3) / 4)),
  );
  return Boolean(stem && skLeft.includes(stem));
}

function collapseContainedSuffixEcho(text: string): string | null {
  if (text.length < SUFFIX_ECHO_MIN * 2) {
    return null;
  }

  // Echoes append near the end — ignore the leading half (history parses must stay cheap).
  const minSplit = Math.max(SUFFIX_ECHO_MIN, Math.floor(text.length / 2));
  const candidates: number[] = [];

  const glued: number[] = [];
  for (const match of text.matchAll(GLUED_SENTENCE_RESTART_RE)) {
    if (typeof match.index === 'number') {
      const end = match.index + match[0].length;
      if (end >= minSplit) {
        glued.push(end);
      }
    }
  }
  candidates.push(...glued.slice(-12));

  const seenHeading = new Map<string, number>();
  for (const match of text.matchAll(MARKDOWN_HEADING_RE)) {
    if (typeof match.index !== 'number') {
      continue;
    }
    const key = semanticProseKey(match[0]);
    if (!key) {
      continue;
    }
    if (!seenHeading.has(key)) {
      seenHeading.set(key, match.index);
      continue;
    }
    if (match.index >= minSplit) {
      candidates.push(match.index);
    }
  }

  if (candidates.length === 0) {
    return null;
  }

  for (const split of [...new Set(candidates)].sort((a, b) => a - b)) {
    const left = text.slice(0, split).replace(/\s+$/u, '');
    const right = text.slice(split).replace(/^\s+/u, '');
    if (suffixIsEchoOfPrefix(left, right)) {
      return left;
    }
  }
  return null;
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

  const contained = collapseContainedSuffixEcho(normalized);
  if (contained !== null) {
    return contained;
  }

  return text;
}

export function dedupeProseText(text: string): string {
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

export function mergeAdjacentDuplicateTextSegments(segments: AgentTranscriptSegment[]): AgentTranscriptSegment[] {
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

export function mergeAdjacentResearchSegments(segments: AgentTranscriptSegment[]): AgentTranscriptSegment[] {
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

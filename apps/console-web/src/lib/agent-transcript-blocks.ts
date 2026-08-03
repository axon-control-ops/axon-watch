/** Parse block-annotated agent transcripts (:::thinking / :::edit / :::tool / :::terminal). */
/** Parse caching is extracted to ./agent-transcript/parse-cache.ts. */
/** Callers should keep importing from this module; exports are unchanged. */

import { sanitizeAgentThinkingForOperator, THINKING_SPEECH_FALLBACK } from './agent-live-line-view';
import { tryParseClarifyingMarkdown } from './agent-question-view';
import { tryParseLegacyLeadFanOutText } from './lead-fan-out-card';
import { looksLikeLeadStandupReport } from './lead-standup-card';

export type {
  AgentTranscriptSegment,
  ResearchTranscriptItem,
} from './agent-transcript/types';
export type { ParseAgentTranscriptOptions } from './agent-transcript/parse-transcript-blocks';
export {
  parseAgentTranscriptBlocksUncached,
} from './agent-transcript/parse-transcript-blocks';
export {
  dedupeProseText,
  dedupeTextSegmentsGlobally,
  mergeAdjacentDuplicateTextSegments,
  mergeAdjacentResearchSegments,
} from './agent-transcript/prose-dedupe';

import type { AgentTranscriptSegment } from './agent-transcript/types';
import {
  parseAgentTranscriptBlocksUncached,
} from './agent-transcript/parse-transcript-blocks';
export { parseAgentTranscriptBlocks } from './agent-transcript/parse-cache';
import { parseAgentTranscriptBlocks } from './agent-transcript/parse-cache';

export function agentContentHasTranscriptBlocks(content: string): boolean {
  if (
    /^:::(thinking|edit|tool|plan|ask|terminal|research|image|debug-reproduce|lead-fan-out)\b/m.test(
      content,
    )
  ) {
    return true;
  }
  // A runtime can return an ordinary numbered clarification instead of the
  // preferred :::ask fence. The parser already upgrades that form, but the
  // conversation surface used to gate the parser behind this function and
  // therefore rendered it as inert markdown. Keep the render gate aligned
  // with the parser so an operator never hears "choose on the ask card" with
  // no card available to choose from.
  if (tryParseClarifyingMarkdown(content) != null) {
    return true;
  }
  // Legacy Lead essays (pre-fence) still get the cinematic fan-out / stand-up cards.
  return (
    tryParseLegacyLeadFanOutText(content) != null || looksLikeLeadStandupReport(content)
  );
}

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

export function prepareAgentTranscriptSegmentsForDisplay(
  content: string,
  options?: { collapseClosedEditsAt?: number },
): AgentTranscriptSegment[] {
  const threshold = options?.collapseClosedEditsAt ?? 12;
  const editCount = countAgentTranscriptHeaders(content).edit;
  const segments =
    editCount >= threshold
      ? parseAgentTranscriptBlocksUncached(content, { omitClosedEditDiffs: true })
      : parseAgentTranscriptBlocks(content);
  return collapseClosedEditSegmentsForDisplay(segments, threshold);
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
  const flattened = (sanitized || THINKING_SPEECH_FALLBACK).replace(/\s+/g, ' ').trim();
  if (flattened.length <= maxLength) {
    return flattened;
  }
  return `${flattened.slice(0, maxLength - 1).trimEnd()}…`;
}

export function normalizeEditedFilePath(path: string): string {
  const normalized = path.trim().replace(/\\/g, '/');
  if (!normalized || normalized.startsWith('/')) {
    return fileBaseName(normalized);
  }
  return normalized;
}

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

import type { AgentTranscriptSegment } from './types';
import {
  parseAgentTranscriptBlocksUncached,
  type ParseAgentTranscriptOptions,
} from './parse-transcript-blocks';

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

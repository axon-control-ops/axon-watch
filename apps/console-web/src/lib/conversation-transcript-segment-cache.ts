/** Cached transcript segment prep so streaming turns do not re-parse every tick. */

import { prepareAgentTranscriptSegmentsForDisplay } from './agent-transcript-blocks';

type TranscriptSegmentCacheEntry = {
  content: string;
  contentLength: number;
  contentTail: string;
  segments: ReturnType<typeof prepareAgentTranscriptSegmentsForDisplay>;
  atMs: number;
};

const STREAM_SEGMENT_MIN_INTERVAL_MS = 120;
const STREAM_SEGMENT_MIN_GROWTH = 1500;
const SEGMENT_CACHE_LIMIT = 80;

export function createTranscriptSegmentCache() {
  const cache = new Map<string, TranscriptSegmentCacheEntry>();

  function transcriptSegments(messageId: string, content: string, streaming: boolean) {
    const cached = cache.get(messageId);
    if (!streaming && cached?.content === content) {
      return cached.segments;
    }

    // Large agent turns (100+ file edits) must not mount a diff card per file on
    // every stream tick — that is what freezes the console ("Page Unresponsive").
    if (streaming) {
      const now = Date.now();
      const previousTailStart = Math.max(0, (cached?.contentLength ?? 0) - 64);
      const previousContentStillPrefix =
        Boolean(cached) &&
        content.length >= cached!.contentLength &&
        content.slice(previousTailStart, cached!.contentLength) === cached!.contentTail;
      if (
        cached &&
        now - cached.atMs < STREAM_SEGMENT_MIN_INTERVAL_MS &&
        content.length - cached.contentLength < STREAM_SEGMENT_MIN_GROWTH &&
        previousContentStillPrefix
      ) {
        return cached.segments;
      }
    }

    const segments = prepareAgentTranscriptSegmentsForDisplay(content, {
      collapseClosedEditsAt: 8,
    });
    cache.set(messageId, {
      content,
      contentLength: content.length,
      contentTail: content.slice(-64),
      segments,
      atMs: Date.now(),
    });
    // Cover the complete bounded transcript window without unbounded growth.
    if (cache.size > SEGMENT_CACHE_LIMIT) {
      const oldest = cache.keys().next().value;
      if (oldest !== undefined) {
        cache.delete(oldest);
      }
    }
    return segments;
  }

  return { transcriptSegments };
}

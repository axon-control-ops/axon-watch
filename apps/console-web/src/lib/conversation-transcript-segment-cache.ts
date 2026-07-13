/** Cached transcript segment prep so streaming turns do not re-parse every tick. */

import { prepareAgentTranscriptSegmentsForDisplay } from './agent-transcript-blocks';

type TranscriptSegmentCacheEntry = {
  contentLength: number;
  contentTail: string;
  segments: ReturnType<typeof prepareAgentTranscriptSegmentsForDisplay>;
  atMs: number;
};

const STREAM_SEGMENT_MIN_INTERVAL_MS = 120;
const STREAM_SEGMENT_MIN_GROWTH = 1500;

export function createTranscriptSegmentCache() {
  const cache = new Map<string, TranscriptSegmentCacheEntry>();

  function transcriptSegments(messageId: string, content: string, streaming: boolean) {
    // Large agent turns (100+ file edits) must not mount a diff card per file on
    // every stream tick — that is what freezes the console ("Page Unresponsive").
    if (streaming) {
      const cached = cache.get(messageId);
      const now = Date.now();
      if (
        cached &&
        now - cached.atMs < STREAM_SEGMENT_MIN_INTERVAL_MS &&
        content.length - cached.contentLength < STREAM_SEGMENT_MIN_GROWTH &&
        content.endsWith(cached.contentTail)
      ) {
        return cached.segments;
      }
    }

    const segments = prepareAgentTranscriptSegmentsForDisplay(content, {
      collapseClosedEditsAt: 8,
    });
    cache.set(messageId, {
      contentLength: content.length,
      contentTail: content.slice(-64),
      segments,
      atMs: Date.now(),
    });
    if (!streaming) {
      // Keep completed turns cheap to re-render without unbounded growth.
      if (cache.size > 12) {
        const oldest = cache.keys().next().value;
        if (oldest !== undefined) {
          cache.delete(oldest);
        }
      }
    }
    return segments;
  }

  return { transcriptSegments };
}

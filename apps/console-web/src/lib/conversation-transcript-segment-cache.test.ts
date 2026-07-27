import { afterEach, describe, expect, it, vi } from 'vitest';

import { createTranscriptSegmentCache } from './conversation-transcript-segment-cache';

describe('conversation transcript segment cache', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('returns the same segments within the stream throttle window', () => {
    let now = 1_000;
    vi.spyOn(Date, 'now').mockImplementation(() => now);
    const cache = createTranscriptSegmentCache();
    const messageId = 'msg_stream';
    const content = 'Hello world';
    const a = cache.transcriptSegments(messageId, content, true);
    now = 1_050;
    const b = cache.transcriptSegments(messageId, content, true);
    expect(b).toBe(a);
  });

  it('throttles normal appended stream deltas', () => {
    let now = 1_000;
    vi.spyOn(Date, 'now').mockImplementation(() => now);
    const cache = createTranscriptSegmentCache();
    const a = cache.transcriptSegments('msg_append', ':::thinking\nChecking', true);
    now = 1_050;
    const b = cache.transcriptSegments(
      'msg_append',
      ':::thinking\nChecking the current implementation',
      true,
    );
    expect(b).toBe(a);
  });

  it('reuses completed segments across a full transcript window', () => {
    const cache = createTranscriptSegmentCache();
    const first = cache.transcriptSegments('msg_0', ':::thinking\nFirst\n:::', false);
    for (let index = 1; index < 40; index += 1) {
      cache.transcriptSegments(`msg_${index}`, `:::thinking\n${index}\n:::`, false);
    }
    expect(cache.transcriptSegments('msg_0', ':::thinking\nFirst\n:::', false)).toBe(first);
  });

  it('reparses after enough growth past the throttle window', () => {
    let now = 1_000;
    vi.spyOn(Date, 'now').mockImplementation(() => now);
    const cache = createTranscriptSegmentCache();
    const messageId = 'msg_growth';
    const first = 'x';
    const a = cache.transcriptSegments(messageId, first, true);
    now = 1_200;
    const grown = first + 'y'.repeat(1600);
    const b = cache.transcriptSegments(messageId, grown, true);
    expect(b).not.toBe(a);
  });
});

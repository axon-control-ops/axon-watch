import { describe, expect, it } from 'vitest';

import { parseAgentTranscriptBlocks } from './agent-transcript-blocks';

describe('agent transcript image blocks', () => {
  it('parses completed image blocks from transcript markers', () => {
    const segments = parseAgentTranscriptBlocks(
      'Mockup ready.\n\n:::image assets/mockup.png\n:::\n\nLet me know what you think.',
    );

    expect(segments).toEqual([
      { kind: 'text', text: 'Mockup ready.' },
      { kind: 'image', path: 'assets/mockup.png', open: false },
      { kind: 'text', text: 'Let me know what you think.' },
    ]);
  });
});

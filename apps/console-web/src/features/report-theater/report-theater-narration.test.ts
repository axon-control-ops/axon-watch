import { describe, expect, it, vi } from 'vitest';

import { narrateReportTheater } from './report-theater-narration';

describe('narrateReportTheater', () => {
  it('shows each stage before speaking and invokes onCommitted after complete', async () => {
    const events: string[] = [];
    const speak = vi.fn(async (line: string) => {
      events.push(`speak:${line}`);
    });
    const setStageIndex = vi.fn((index: number) => {
      events.push(`stage:${index}`);
    });
    const onComplete = vi.fn(() => {
      events.push('complete');
    });
    const onCommitted = vi.fn(async () => {
      events.push('committed');
    });

    await narrateReportTheater(
      [
        { id: 'attention', title: 'Attention', lines: ['Signal A'] },
        { id: 'next_move', title: 'Next move', lines: ["I'll switch us there"] },
      ],
      {
        speak,
        setStageIndex,
        onComplete,
        onCommitted,
        isCancelled: () => false,
      },
    );

    expect(events).toEqual([
      "speak:Here's the stand-up.",
      'stage:0',
      'speak:Attention. Signal A.',
      'stage:1',
      "speak:Next move. I'll switch us there.",
      'complete',
      'committed',
    ]);
    expect(onCommitted).toHaveBeenCalledTimes(1);
  });
});

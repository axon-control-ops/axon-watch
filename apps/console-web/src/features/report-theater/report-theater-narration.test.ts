import { describe, expect, it, vi } from 'vitest';

import { narrateReportTheater, polishTheaterLine } from './report-theater-narration';

describe('polishTheaterLine', () => {
  it('collapses CLI laundry lists into a short operator line', () => {
    const polished = polishTheaterLine(
      'Mira (lead) failed — Lane B (agent) cannot start because no CLI runtime is ready: '
        + 'Codex CLI (local) unavailable; Cursor auth probe timed out; invocation ID: abc-123',
    );
    expect(polished.toLowerCase()).toContain('no cli runtime is ready');
    expect(polished.toLowerCase()).not.toContain('invocation');
    expect(polished.length).toBeLessThanOrEqual(160);
  });
});

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
      'speak:Stand-up online.',
      'stage:0',
      'speak:Attention. Signal A.',
      'stage:1',
      "speak:Next move. I'll switch us there.",
      'complete',
      'committed',
    ]);
    expect(onCommitted).toHaveBeenCalledTimes(1);
  });

  it('routes completed teammates through individual reporting turns', async () => {
    const turns: Array<{ line: string; speaker: string | null }> = [];

    await narrateReportTheater(
      [
        {
          id: 'work_in_flight',
          title: 'Work in flight',
          lines: [
            'Marco (Backend) just completed',
            'Soren (Integrations) just completed',
          ],
        },
      ],
      {
        speak: async (line, speakerName) => {
          turns.push({ line, speaker: speakerName ?? null });
        },
        setStageIndex: () => undefined,
        onComplete: () => undefined,
        isCancelled: () => false,
      },
    );

    expect(turns).toContainEqual({ line: 'Work in flight.', speaker: null });
    expect(turns).toContainEqual({
      line: 'Marco here. I just completed my shift.',
      speaker: 'Marco',
    });
    expect(turns).toContainEqual({
      line: 'Soren here. I just completed my shift.',
      speaker: 'Soren',
    });
  });
});

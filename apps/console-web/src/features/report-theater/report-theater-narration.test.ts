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

  it('strips shell dumps from Lead completion headlines', () => {
    const polished = polishTheaterLine(
      'Mira (lead) completed. terminal ls -la /home/edp/axon-nvme/repos/axon-watch/control-plane.sqlite3 '
        + 'find /home/edp -name control-plane.sqlite 2>/dev/null | head -20',
      800,
    );
    expect(polished.toLowerCase()).toContain('completed');
    expect(polished.toLowerCase()).not.toContain('terminal');
    expect(polished.toLowerCase()).not.toContain('sqlite');
    expect(polished.toLowerCase()).not.toContain('/home/');
  });

  it('rewrites ask-option commit laundry and push failures into clear advise', () => {
    const polished = polishTheaterLine(
      'Dana (lead) completed. Committed successfully with message: Selected option 1: Yes. '
        + 'Push failed: git push failed',
      800,
    );
    expect(polished).toContain('Committed after your choice');
    expect(polished.toLowerCase()).toContain('push did not');
    expect(polished.toLowerCase()).not.toContain('selected option');
    expect(polished.toLowerCase()).not.toContain('push failed: git push failed');
  });

  it('uses push stderr instead of guessing authentication or branch protection', () => {
    const polished = polishTheaterLine(
      'Dana completed. Push failed: git push failed: updates were rejected '
        + '(non-fast-forward); fetch first',
      800,
    );
    expect(polished.toLowerCase()).toContain('remote branch is ahead');
    expect(polished.toLowerCase()).not.toContain('authentication');
    expect(polished.toLowerCase()).not.toContain('branch protection');
  });

  it('keeps spoken Lead bodies concise by default', () => {
    const polished = polishTheaterLine(
      `Mira completed. ${'Detailed receipt evidence and implementation notes. '.repeat(20)}`,
    );
    expect(polished.length).toBeLessThanOrEqual(220);
    expect(polished.endsWith('…')).toBe(true);
  });
});

describe('narrateReportTheater', () => {
  it('shows each stage when playback starts and commits after completion', async () => {
    const events: string[] = [];
    const speak = vi.fn(async (
      line: string,
      _speakerName?: string | null,
      onPlaybackStart?: () => void,
    ) => {
      onPlaybackStart?.();
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
        speak: async (line, speakerName, onPlaybackStart) => {
          onPlaybackStart?.();
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

import { describe, expect, it } from 'vitest';

import { agentMilestoneFallbackLine, progressFallbackLine } from './kairo-progress-fallback';

describe('kairo-progress-fallback', () => {
  it('builds concise research narration', () => {
    expect(
      progressFallbackLine({
        eventType: 'research_started',
        context: { research_query: 'Axon-X parity blockers' },
      }),
    ).toContain('Axon-X parity blockers');

    expect(
      progressFallbackLine({
        eventType: 'research_complete',
        context: { research_query: 'Axon-X parity blockers' },
      }),
    ).toContain('finished');
  });

  it('keeps verification and error copy operator-facing', () => {
    expect(progressFallbackLine({ eventType: 'verified_complete' })).toContain('verified');
    expect(
      progressFallbackLine({
        eventType: 'stream_error',
        context: { failure_summary: 'runtime stream failed' },
      }),
    ).toContain('runtime stream failed');
  });

  it('avoids the canned run-start line for greetings and questions', () => {
    expect(
      progressFallbackLine({
        eventType: 'run_started',
        context: { operator_prompt: 'Hey VAXON' },
      }),
    ).toBe('');
    expect(
      progressFallbackLine({
        eventType: 'run_started',
        context: { operator_prompt: 'Walk me through pending worker agents' },
      }),
    ).toBe('');
    expect(
      progressFallbackLine({
        eventType: 'run_started',
        context: {
          operator_prompt:
            'What do we need for faster TTS — and what voice engine are they using?',
        },
      }),
    ).toBe('');
    expect(
      progressFallbackLine({
        eventType: 'run_started',
        context: { operator_prompt: 'Fix the terminal scrollback bug' },
      }),
    ).toBe('');
  });

  it('mirrors agent bookend fallbacks when speak is unavailable', () => {
    expect(
      agentMilestoneFallbackLine({
        milestoneKey: 'done',
        context: { task_summary: 'Updated the voice fallback path.' },
      }),
    ).toBe('Updated the voice fallback path.');

    expect(
      agentMilestoneFallbackLine({
        milestoneKey: 'failed',
        context: { failure_summary: 'runtime stream failed' },
      }),
    ).toContain('runtime stream failed');

    expect(
      agentMilestoneFallbackLine({
        milestoneKey: 'start',
        context: { operator_prompt: 'Fix the terminal scrollback bug' },
      }),
    ).toBe('');
  });
});


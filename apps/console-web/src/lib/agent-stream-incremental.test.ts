import { describe, expect, it } from 'vitest';

import { createAgentStreamIncrementalState } from './agent-stream-incremental';
import {
  narrationMilestonesForDelta,
  resolveStreamingActivity,
} from './kairo-agent-narration';

const LONG_THINKING_BODY =
  "I'm starting to analyze the rendering issues the user wants fixed. They want table rendering to work in markdown previews.";
const STAGE_1 = ':::thinking\nChecking the file';
const STAGE_1_LONG = `:::thinking\n${LONG_THINKING_BODY}`;
const STAGE_2 = ':::thinking\nChecking the file.\n:::\n\n:::tool Read README.md\n';
const STAGE_3 = `${STAGE_2}\n:::edit README.md +1 -0\n--- a\n+++ b\n+<!-- hi -->\n:::\nDONE`;

function feedIncrementalDeltas(content: string): ReturnType<typeof createAgentStreamIncrementalState> {
  const state = createAgentStreamIncrementalState();
  const lines = content.split('\n');
  let accumulated = '';
  for (const line of lines) {
    accumulated = accumulated ? `${accumulated}\n${line}` : line;
    state.consumeFullContent(accumulated);
  }
  return state;
}

function buildLargeEditTranscript(fileCount: number, linesPerDiff = 4): string {
  const chunks: string[] = [':::thinking', 'Updating many files', ':::'];
  for (let index = 0; index < fileCount; index += 1) {
    const diffLines = Array.from({ length: linesPerDiff }, (_, line) => `+line ${line} file ${index}`);
    chunks.push(`:::edit apps/console-web/src/file-${index}.ts +${linesPerDiff} -0`);
    chunks.push(...diffLines);
    chunks.push(':::');
  }
  chunks.push(':::terminal curl localhost', 'ok', ':::');
  return chunks.join('\n');
}

describe('createAgentStreamIncrementalState', () => {
  it('matches milestone deltas from the legacy full-content scanner', () => {
    const state = createAgentStreamIncrementalState();
    const stages = ['', STAGE_1, STAGE_2, STAGE_3];
    for (let index = 1; index < stages.length; index += 1) {
      const previous = stages[index - 1];
      const current = stages[index];
      const legacy = narrationMilestonesForDelta(previous, current);
      const incremental = state.consumeFullContent(current);
      expect(incremental).toEqual(legacy);
    }
  });

  it('matches streaming activity from the legacy resolver', () => {
    const state = feedIncrementalDeltas(STAGE_1_LONG);
    expect(state.toStreamingActivityView()).toEqual(resolveStreamingActivity(STAGE_1_LONG));

    const state2 = feedIncrementalDeltas(STAGE_2);
    expect(state2.toStreamingActivityView()).toEqual(resolveStreamingActivity(STAGE_2));
    expect(state2.toStreamingActivityView(true)).toEqual(resolveStreamingActivity(STAGE_2, true));
  });

  it('exposes the complete first thinking block for one verbatim narration', () => {
    const state = createAgentStreamIncrementalState();
    state.consumeFullContent(
      ':::thinking\nContinuing investigation of the deploy failure. Checking CI status and git status.\n:::\n',
    );
    expect(state.takeCompletedThinkingSpeech()).toBe(
      'Continuing investigation of the deploy failure. Checking CI status and git status.',
    );
    expect(state.takeCompletedThinkingSpeech()).toBeNull();
  });

  it('tracks header counts without re-scanning prior transcript', () => {
    const state = feedIncrementalDeltas(buildLargeEditTranscript(141));
    expect(state.toCounts()).toEqual({
      edit: 141,
      terminal: 1,
      tool: 0,
      research: 0,
    });
  });

  it('stays fast when many small deltas arrive during a large edit fan-out', () => {
    const content = buildLargeEditTranscript(141);
    const state = createAgentStreamIncrementalState();
    const started = Date.now();
    let accumulated = '';
    for (const char of content) {
      accumulated += char;
      state.consumeFullContent(accumulated);
    }
    const elapsedMs = Date.now() - started;
    expect(state.toCounts().edit).toBe(141);
    expect(elapsedMs).toBeLessThan(250);
  });
});

import { describe, expect, it } from 'vitest';

import {
  countAgentTranscriptHeaders,
  prepareAgentTranscriptSegmentsForDisplay,
} from './agent-transcript-blocks';
import { summarizeIdeAgentActivity } from './ide-agent-activity-view';
import {
  collectIdeAgentEditSummariesFromThread,
  extractIdeAgentEditSummaries,
} from './ide-agent-center-view';

function buildLargeEditTranscript(fileCount: number, linesPerDiff = 40): string {
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

describe('large agent transcript freeze mitigations', () => {
  it('collapses 141 closed edits into one display summary without edit cards', () => {
    const content = buildLargeEditTranscript(141);
    const started = Date.now();
    const segments = prepareAgentTranscriptSegmentsForDisplay(content, {
      collapseClosedEditsAt: 8,
    });
    const elapsedMs = Date.now() - started;

    expect(segments.filter((segment) => segment.kind === 'edit')).toHaveLength(0);
    expect(segments).toContainEqual({ kind: 'tool', label: 'Updated 141 files' });
    expect(segments.some((segment) => segment.kind === 'terminal')).toBe(true);
    // Structural + soft budget: this path must stay interactive on stream ticks.
    expect(elapsedMs).toBeLessThan(750);
  });

  it('counts activity chips without retaining edit bodies', () => {
    const content = buildLargeEditTranscript(141);
    const summary = summarizeIdeAgentActivity(content);
    expect(summary.fileCount).toBe(141);
    expect(summary.terminalCount).toBe(1);
    expect(summary.chips.some((chip) => chip.label === '141 files')).toBe(true);
    expect(countAgentTranscriptHeaders(content).edit).toBe(141);
  });

  it('collects review-strip paths without storing diffs until requested', () => {
    const content = buildLargeEditTranscript(141, 20);
    const headers = collectIdeAgentEditSummariesFromThread(
      [{ message_id: 'msg_1', role: 'agent', content }],
      { includeDiff: false },
    );
    expect(headers).toHaveLength(141);
    expect(headers.every((edit) => edit.diff === '')).toBe(true);

    const withDiff = extractIdeAgentEditSummaries(content, 'msg_1', { includeDiff: true });
    expect(withDiff[0]?.diff.includes('+line 0 file 0')).toBe(true);
  });
});

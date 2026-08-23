import { describe, expect, it } from 'vitest';

import {
  agentEditEventLabel,
  agentEditOperation,
  agentEditOperationLabel,
} from './agent-edit-operation';

describe('agent edit operation labels', () => {
  it('detects created files from unified diff metadata', () => {
    expect(
      agentEditOperation({
        added: 8,
        removed: 0,
        diff: ['diff --git a/new.ts b/new.ts', 'new file mode 100644', '--- /dev/null', '+++ b/new.ts'].join('\n'),
      }),
    ).toBe('created');
  });

  it('detects created files from Claude write-style empty-old hunks', () => {
    expect(
      agentEditOperation({
        added: 2,
        removed: 0,
        diff: ['--- a/src/new-panel.ts', '+++ b/src/new-panel.ts', '@@ -0,0 +1,2 @@', '+one', '+two'].join('\n'),
      }),
    ).toBe('created');
  });

  it('detects deleted files from unified diff metadata', () => {
    expect(
      agentEditOperation({
        added: 0,
        removed: 4,
        diff: ['diff --git a/old.ts b/old.ts', 'deleted file mode 100644', '--- a/old.ts', '+++ /dev/null'].join('\n'),
      }),
    ).toBe('deleted');
  });

  it('detects deleted files from empty-new hunks', () => {
    expect(
      agentEditOperation({
        added: 0,
        removed: 2,
        diff: ['--- a/src/old-panel.ts', '+++ b/src/old-panel.ts', '@@ -1,2 +0,0 @@', '-one', '-two'].join('\n'),
      }),
    ).toBe('deleted');
  });

  it('keeps line-only changes as edited and zero-diff receipts as checked', () => {
    expect(agentEditOperation({ added: 2, removed: 1, diff: '@@\n-old\n+new' })).toBe('edited');
    expect(agentEditOperation({ added: 0, removed: 0, diff: '' })).toBe('touched');
    expect(agentEditOperation({ added: 3, removed: 0 })).toBe('changed');
    expect(agentEditOperationLabel('touched')).toBe('Checked file');
  });

  it('formats compact transcript events consistently', () => {
    expect(
      agentEditEventLabel({
        path: 'src/App.vue',
        added: 3,
        removed: 0,
      }),
    ).toBe('File change: src/App.vue');
  });
});

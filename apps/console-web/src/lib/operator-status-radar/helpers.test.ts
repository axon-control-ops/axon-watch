import { describe, expect, it } from 'vitest';

import { firstMeaningfulLine } from './helpers';

describe('operator status radar helpers', () => {
  it('uses file-operation labels for transcript edit receipts', () => {
    const content = [
      ':::edit src/new-panel.ts +2 -0',
      'diff --git a/src/new-panel.ts b/src/new-panel.ts',
      'new file mode 100644',
      '--- /dev/null',
      '+++ b/src/new-panel.ts',
      '+export const ok = true;',
      ':::',
    ].join('\n');

    expect(firstMeaningfulLine(content)).toBe('Created file: src/new-panel.ts');
  });
});

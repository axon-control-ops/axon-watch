import { describe, expect, it } from 'vitest';

import {
  buildMentionFileRows,
  mentionInsertionForPath,
} from './composer-mention-files-view';

describe('composer-mention-files-view', () => {
  it('filters workspace files by path query', () => {
    const rows = buildMentionFileRows(
      [
        { path: 'apps/console-web/src/api/client.ts' },
        { path: 'README.md' },
      ],
      'client',
    );
    expect(rows).toHaveLength(1);
    expect(rows[0]?.path).toContain('client.ts');
  });

  it('builds a file mention insertion', () => {
    expect(mentionInsertionForPath('README.md')).toBe('@file:README.md ');
  });
});

import { describe, expect, it } from 'vitest';

import { columnTone, parseDependencies } from './operator-task-board-helpers';

describe('operator-task-board-helpers', () => {
  it('maps column ids to tone classes', () => {
    expect(columnTone('needs_attention')).toBe('needs');
    expect(columnTone('in_progress')).toBe('live');
    expect(columnTone('done')).toBe('done');
    expect(columnTone('waiting')).toBe('waiting');
  });

  it('parses comma- and whitespace-separated dependency ids', () => {
    expect(parseDependencies('a, b  c')).toEqual(['a', 'b', 'c']);
    expect(parseDependencies('  ')).toEqual([]);
  });
});

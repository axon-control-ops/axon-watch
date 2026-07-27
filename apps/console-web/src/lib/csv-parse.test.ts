import { describe, expect, it } from 'vitest';

import { parseDelimitedTable, splitCsvRow } from './csv-parse';

describe('csv-parse', () => {
  it('splits quoted csv rows', () => {
    expect(splitCsvRow('"a,b",c')).toEqual(['a,b', 'c']);
  });

  it('parses headered csv tables', () => {
    const table = parseDelimitedTable('name,role\nDana,Lead\nMarco,Backend');
    expect(table).toEqual({
      headers: ['name', 'role'],
      rows: [
        ['Dana', 'Lead'],
        ['Marco', 'Backend'],
      ],
      hasHeader: true,
    });
  });

  it('parses tsv with tab delimiter hint', () => {
    const table = parseDelimitedTable('a\tb\n1\t2', '\t');
    expect(table?.headers).toEqual(['a', 'b']);
    expect(table?.rows).toEqual([['1', '2']]);
  });
});

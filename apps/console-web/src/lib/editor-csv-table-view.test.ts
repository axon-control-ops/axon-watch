import { describe, expect, it } from 'vitest';

import { csvTablePreviewFromRaw } from './editor-csv-table-view';

describe('editor-csv-table-view', () => {
  it('renders an html table for csv content', () => {
    const html = csvTablePreviewFromRaw('status,name\npaid,Ada');
    expect(html).toContain('<table>');
    expect(html).toContain('status');
    expect(html).toContain('paid');
    expect(html).toContain('Ada');
  });
});

import { parseDelimitedTable, type CsvTable } from './csv-parse';

function escapeHtml(value: string): string {
  return value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

export function buildCsvTablePreview(table: CsvTable | null): string {
  if (!table || !table.rows.length) {
    return '<p class="editor-csv-preview__empty">No tabular rows to display.</p>';
  }

  const headerCells = table.headers
    .map((header) => `<th scope="col">${escapeHtml(header)}</th>`)
    .join('');

  const bodyRows = table.rows
    .map((row) => {
      const cells = row.map((cell) => `<td>${escapeHtml(cell)}</td>`).join('');
      return `<tr>${cells}</tr>`;
    })
    .join('');

  return `<div class="markdown-table-wrap editor-csv-preview__table-wrap"><table><thead><tr>${headerCells}</tr></thead><tbody>${bodyRows}</tbody></table></div>`;
}

export function csvTablePreviewFromRaw(raw: string, filePath?: string | null): string {
  const extension = filePath?.split('.').pop()?.toLowerCase() ?? '';
  const delimiterHint = extension === 'tsv' ? '\t' : undefined;
  return buildCsvTablePreview(parseDelimitedTable(raw, delimiterHint));
}

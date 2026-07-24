export type CsvTable = {
  headers: string[];
  rows: string[][];
  hasHeader: boolean;
};

/** RFC4180-style row split with quoted fields. */
export function splitCsvRow(line: string, delimiter = ','): string[] {
  const cells: string[] = [];
  let current = '';
  let inQuotes = false;

  for (let index = 0; index < line.length; index += 1) {
    const char = line[index];
    if (char === '"') {
      if (inQuotes && line[index + 1] === '"') {
        current += '"';
        index += 1;
      } else {
        inQuotes = !inQuotes;
      }
      continue;
    }
    if (char === delimiter && !inQuotes) {
      cells.push(stripCsvCell(current));
      current = '';
      continue;
    }
    current += char;
  }

  cells.push(stripCsvCell(current));
  return cells;
}

function stripCsvCell(value: string): string {
  return value.trim().replace(/^['"]|['"]$/g, '');
}

function detectDelimiter(sampleLines: string[]): string {
  const candidates = [',', '\t', ';', '|'];
  let best = ',';
  let bestScore = -1;

  for (const delimiter of candidates) {
    const counts = sampleLines.map((line) => splitCsvRow(line, delimiter).length);
    const max = Math.max(...counts, 0);
    const min = Math.min(...counts, max);
    if (max <= 1) {
      continue;
    }
    const score = max * 10 - (max - min);
    if (score > bestScore) {
      bestScore = score;
      best = delimiter;
    }
  }

  return best;
}

function looksLikeHeaderRow(cells: string[]): boolean {
  if (cells.length < 2) {
    return false;
  }
  const nonEmpty = cells.filter((cell) => cell.trim().length > 0);
  if (nonEmpty.length < 2) {
    return false;
  }
  const numericCells = nonEmpty.filter((cell) => /^-?\d+(?:\.\d+)?$/.test(cell.trim()));
  return numericCells.length < nonEmpty.length * 0.6;
}

/** Parse delimited text into a table for preview rendering. */
export function parseDelimitedTable(raw: string, delimiterHint?: '\t' | ',' | ';' | '|'): CsvTable | null {
  const lines = raw
    .split(/\r?\n/)
    .map((line) => line.trimEnd())
    .filter((line) => line.length > 0);

  if (!lines.length) {
    return null;
  }

  const delimiter = delimiterHint ?? detectDelimiter(lines.slice(0, Math.min(lines.length, 8)));
  const matrix = lines.map((line) => splitCsvRow(line, delimiter));
  const columnCount = Math.max(...matrix.map((row) => row.length), 0);
  if (columnCount <= 1 && matrix.length <= 1) {
    return null;
  }

  const normalized = matrix.map((row) => {
    const next = [...row];
    while (next.length < columnCount) {
      next.push('');
    }
    return next.slice(0, columnCount);
  });

  const hasHeader = looksLikeHeaderRow(normalized[0] ?? []);
  const headers = hasHeader
    ? (normalized[0] ?? []).map((cell, index) => cell.trim() || `Column ${index + 1}`)
    : Array.from({ length: columnCount }, (_, index) => `Column ${index + 1}`);
  const rows = hasHeader ? normalized.slice(1) : normalized;

  return { headers, rows, hasHeader };
}

export function isTabularFilePath(path: string): boolean {
  const extension = path.split('.').pop()?.toLowerCase() ?? '';
  return extension === 'csv' || extension === 'tsv';
}

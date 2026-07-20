export type MentionFileRow = {
  id: string;
  path: string;
  label: string;
  kind: 'file';
};

export function buildMentionFileRows(
  entries: Array<{ path: string }>,
  query: string,
  limit = 12,
): MentionFileRow[] {
  const normalized = query.trim().toLowerCase().replace(/^@/, '');
  const filtered = entries.filter((entry) => {
    if (!normalized) {
      return true;
    }
    return entry.path.toLowerCase().includes(normalized);
  });
  return filtered.slice(0, limit).map((entry) => ({
    id: `file:${entry.path}`,
    path: entry.path,
    label: entry.path,
    kind: 'file' as const,
  }));
}

export function mentionInsertionForPath(path: string): string {
  return `@file:${path} `;
}

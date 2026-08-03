import type { CodexRuntimeStatusSnapshot } from '../api/control-plane';
import type { CursorCatalogRow } from './cursor-catalog-view';

export function buildCodexCatalogRows(
  snapshot: CodexRuntimeStatusSnapshot | null,
): CursorCatalogRow[] {
  const rows: CursorCatalogRow[] = [
    {
      id: 'auto',
      label: 'Auto',
      description: 'Let your signed-in Codex / ChatGPT account choose the default model.',
      available: true,
    },
  ];
  const seen = new Set(rows.map((row) => row.id));
  for (const model of snapshot?.available_models ?? snapshot?.codex_models ?? []) {
    const id = String(model.id ?? '').trim();
    if (!id || seen.has(id)) continue;
    seen.add(id);
    rows.push({
      id,
      label: String(model.label ?? id).trim() || id,
      description: String(model.description ?? 'Codex model available to this account.').trim(),
      ...(model.badge ? { badge: String(model.badge) } : {}),
      available: model.available !== false,
    });
  }
  return rows;
}

export function codexModelLabel(modelId: string, rows: CursorCatalogRow[]): string {
  const normalized = modelId.trim() || 'auto';
  return rows.find((row) => row.id === normalized)?.label ?? (normalized === 'auto' ? 'Auto' : normalized);
}

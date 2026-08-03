import type { CodexRuntimeStatusSnapshot } from '../api/control-plane';
import type { CursorCatalogRow } from './cursor-catalog-view';

export function buildCodexCatalogRows(
  snapshot: CodexRuntimeStatusSnapshot | null,
): CursorCatalogRow[] {
  const rows: CursorCatalogRow[] = [];
  const seen = new Set<string>();
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
  const normalized = modelId.trim();
  if (!normalized || normalized === 'auto') {
    return rows.find((row) => row.available)?.label ?? 'Choose model';
  }
  return rows.find((row) => row.id === normalized)?.label ?? normalized;
}

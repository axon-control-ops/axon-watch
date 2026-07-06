import type { CursorRuntimeStatusSnapshot } from '../api/control-plane';

import {
  CURSOR_PICKER_CURATED_IDS,
  cursorPickerExplicitVisibleModelSet,
  isCursorPickerCuratedModel,
} from './cursor-picker-prefs';

export type CursorCatalogRow = {
  id: string;
  label: string;
  description: string;
  badge?: string;
  available: boolean;
};

export function buildCursorCatalogRows(
  snapshot: CursorRuntimeStatusSnapshot | null,
): CursorCatalogRow[] {
  const rows: CursorCatalogRow[] = [];
  const seen = new Set<string>();

  const add = (items: Array<{ id?: string; label?: string; description?: string; badge?: string; available?: boolean }>) => {
    for (const item of items) {
      const id = String(item.id ?? '').trim();
      if (!id || seen.has(id)) {
        continue;
      }
      seen.add(id);
      const row: CursorCatalogRow = {
        id,
        label: String(item.label ?? id).trim() || id,
        description: String(item.description ?? item.label ?? '').trim(),
        available: item.available !== false,
      };
      const badge = String(item.badge ?? '').trim();
      if (badge) {
        row.badge = badge;
      }
      rows.push(row);
    }
  };

  add([
    {
      id: 'auto',
      label: 'Auto',
      description: "Use Cursor's live default unless you pin a catalog model.",
    },
  ]);

  const liveRows = snapshot?.available_models ?? [];
  if (liveRows.length) {
    add(liveRows);
  } else {
    add(snapshot?.cursor_models ?? []);
  }

  return rows;
}

export function cursorCatalogHasLiveRows(
  snapshot: CursorRuntimeStatusSnapshot | null,
): boolean {
  return Boolean(snapshot?.available_models?.length);
}

export function cursorAutoModelDescription(rows: CursorCatalogRow[]): string {
  return (
    rows.find((row) => row.id === 'auto')?.description
    ?? "Use Cursor's live default unless you pin a catalog model."
  );
}

export function cursorCatalogModelRows(rows: CursorCatalogRow[]): CursorCatalogRow[] {
  return rows.filter((row) => row.id !== 'auto');
}

export function isCursorAutoModel(modelId: string): boolean {
  const normalized = modelId.trim();
  return !normalized || normalized === 'auto';
}

export function cursorPrimaryDisplayIds(input: {
  rows: CursorCatalogRow[];
  activeModelId: string;
  visibleExtraModelIds: string[];
  searchQuery?: string;
}): string[] {
  const models = cursorCatalogModelRows(input.rows);
  const query = String(input.searchQuery ?? '').trim().toLowerCase();
  if (query) {
    return models
      .filter((row) => `${row.label} ${row.id} ${row.description}`.toLowerCase().includes(query))
      .map((row) => row.id);
  }

  const curated = new Set<string>(CURSOR_PICKER_CURATED_IDS);
  const explicit = cursorPickerExplicitVisibleModelSet(input.visibleExtraModelIds);
  explicit.forEach((id) => curated.add(id));
  const activeId = input.activeModelId.trim();
  if (activeId && activeId !== 'auto') {
    curated.add(activeId);
  }

  const available = new Set(models.map((row) => row.id));
  return [...curated].filter((id) => available.has(id));
}

export function cursorPrimaryModelRows(input: {
  rows: CursorCatalogRow[];
  activeModelId: string;
  visibleExtraModelIds: string[];
}): CursorCatalogRow[] {
  if (isCursorAutoModel(input.activeModelId)) {
    return [];
  }

  const ids = new Set(cursorPrimaryDisplayIds(input));
  return cursorCatalogModelRows(input.rows).filter((row) => ids.has(row.id));
}

export function cursorManageModelRows(input: {
  rows: CursorCatalogRow[];
  searchQuery?: string;
}): CursorCatalogRow[] {
  const query = String(input.searchQuery ?? '').trim().toLowerCase();
  let rows = cursorCatalogModelRows(input.rows);
  if (!query) {
    return rows;
  }
  return rows.filter((row) =>
    `${row.label} ${row.id} ${row.description}`.toLowerCase().includes(query),
  );
}

export function cursorExtraModelRows(rows: CursorCatalogRow[]): CursorCatalogRow[] {
  return cursorCatalogModelRows(rows).filter((row) => !isCursorPickerCuratedModel(row.id));
}

export function cursorPickerExtraModelSelected(
  modelId: string,
  visibleExtraModelIds: string[],
): boolean {
  const id = modelId.trim();
  if (!id || id === 'auto') {
    return false;
  }
  return cursorPickerExplicitVisibleModelSet(visibleExtraModelIds).has(id);
}

export function cursorCatalogScopeLabel(visibleExtraModelIds: string[], searchQuery = ''): string {
  if (searchQuery.trim()) {
    return 'Search results';
  }
  if (cursorPickerExplicitVisibleModelSet(visibleExtraModelIds).size) {
    return 'Cursor defaults + selected';
  }
  return 'Cursor defaults';
}

export function cursorCatalogCountLabel(input: {
  rows: CursorCatalogRow[];
  visibleExtraModelIds: string[];
  searchQuery?: string;
}): string {
  const shown = cursorManageModelRows({
    rows: input.rows,
    searchQuery: input.searchQuery,
  }).length;
  const total = cursorCatalogModelRows(input.rows).length;
  const scope = cursorCatalogScopeLabel(input.visibleExtraModelIds, input.searchQuery);
  return `${scope} · ${shown} shown · ${total} total`;
}

export function cursorCatalogStatusLabel(input: {
  loading: boolean;
  snapshot: CursorRuntimeStatusSnapshot | null;
}): string {
  if (input.loading) {
    return 'Refreshing Cursor catalog';
  }
  return cursorCatalogHasLiveRows(input.snapshot)
    ? 'Live Cursor catalog'
    : 'Cached Cursor catalog';
}

export function cursorStaleModelWarning(input: {
  modelId: string;
  rows: CursorCatalogRow[];
  snapshot: CursorRuntimeStatusSnapshot | null;
}): string {
  const id = input.modelId.trim();
  if (!id || id === 'auto') {
    return '';
  }
  const available = input.rows.some((row) => row.id === id && row.available !== false);
  if (available) {
    return '';
  }
  if (!cursorCatalogHasLiveRows(input.snapshot)) {
    return 'Cursor model catalog is still loading. Choose Auto or retry in a moment.';
  }
  return `${id} is not available in the live Cursor CLI catalog. Choose Auto or a listed model.`;
}

export function cursorModelLabel(modelId: string, rows: CursorCatalogRow[]): string {
  const normalized = modelId.trim();
  if (!normalized || normalized === 'auto') {
    return 'Auto';
  }
  return rows.find((row) => row.id === normalized)?.label ?? normalized;
}

export function cursorComposerRuntimeLabel(input: {
  family: string;
  scope: string;
  modelId: string;
  rows: CursorCatalogRow[];
}): string {
  const modelLabel = cursorModelLabel(input.modelId, input.rows);
  return `${input.family} ${input.scope} · ${modelLabel}`;
}

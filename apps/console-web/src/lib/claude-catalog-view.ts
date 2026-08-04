import type { ClaudeRuntimeStatusSnapshot } from '../api/control-plane';

import { composerRuntimeFamilyLabel, type CursorCatalogRow } from './cursor-catalog-view';
import {
  CLAUDE_PICKER_CURATED_IDS,
  CLAUDE_PICKER_DEFAULT_MODEL,
  CLAUDE_PICKER_PRIMARY_IDS,
  claudePickerExplicitVisibleModelSet,
  isClaudePickerCuratedModel,
} from './claude-picker-prefs';

/** Same row shape as CursorCatalogRow — reused rather than redefined. */
export type ClaudeCatalogRow = CursorCatalogRow;

export function buildClaudeCatalogRows(
  snapshot: ClaudeRuntimeStatusSnapshot | null,
): ClaudeCatalogRow[] {
  const rows: ClaudeCatalogRow[] = [];
  const seen = new Set<string>();

  const add = (items: Array<{ id?: string; label?: string; description?: string; badge?: string; available?: boolean }>) => {
    for (const item of items) {
      const id = String(item.id ?? '').trim();
      if (!id || seen.has(id)) {
        continue;
      }
      seen.add(id);
      const row: ClaudeCatalogRow = {
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

  add(
    snapshot?.available_models?.length
      ? snapshot.available_models
      : [
          {
            id: 'auto',
            label: 'Auto',
            description: "Use the Claude Code CLI's own default model unless you pin one below.",
          },
        ],
  );

  return rows;
}

export function claudeAutoModelDescription(rows: ClaudeCatalogRow[]): string {
  return (
    rows.find((row) => row.id === 'auto')?.description
    ?? "Use the Claude Code CLI's own default model unless you pin one below."
  );
}

export function claudeCatalogModelRows(rows: ClaudeCatalogRow[]): ClaudeCatalogRow[] {
  return rows.filter((row) => row.id !== 'auto');
}

export function isClaudeAutoModel(modelId: string): boolean {
  const normalized = modelId.trim();
  return !normalized || normalized === 'auto';
}

export function isClaudePrimaryModel(modelId: string): boolean {
  const normalized = modelId.trim().toLowerCase();
  return (CLAUDE_PICKER_PRIMARY_IDS as readonly string[]).includes(normalized);
}

export function claudePrimaryPickerRows(rows: ClaudeCatalogRow[]): ClaudeCatalogRow[] {
  const models = claudeCatalogModelRows(rows);
  const byId = new Map(models.map((row) => [row.id, row]));
  const ordered: ClaudeCatalogRow[] = [];
  for (const id of CLAUDE_PICKER_PRIMARY_IDS) {
    const row = byId.get(id);
    if (row) {
      ordered.push(row);
    }
  }
  return ordered;
}

export function shouldShowClaudeManualModelCatalog(activeModelId: string): boolean {
  return !isClaudeAutoModel(activeModelId);
}

export function claudePrimaryPickerRowsForActiveModel(input: {
  rows: ClaudeCatalogRow[];
  activeModelId: string;
}): ClaudeCatalogRow[] {
  if (!shouldShowClaudeManualModelCatalog(input.activeModelId)) {
    return [];
  }
  return claudePrimaryPickerRows(input.rows);
}

export function resolveClaudeModel(modelId: string, rows: ClaudeCatalogRow[]): string {
  const normalized = modelId.trim();
  if (!normalized || normalized === 'auto') {
    return normalized || 'auto';
  }
  const match = rows.find((row) => row.id === normalized);
  if (match && match.available !== false) {
    return normalized;
  }
  // Stale / unavailable ids fall back to Claude Code's own default.
  return claudePrimaryPickerRows(rows)[0]?.id ?? CLAUDE_PICKER_DEFAULT_MODEL;
}

export function claudePrimaryDisplayIds(input: {
  rows: ClaudeCatalogRow[];
  activeModelId: string;
  visibleExtraModelIds: string[];
  searchQuery?: string;
}): string[] {
  const models = claudeCatalogModelRows(input.rows);
  const query = String(input.searchQuery ?? '').trim().toLowerCase();
  if (query) {
    return models
      .filter((row) => `${row.label} ${row.id} ${row.description}`.toLowerCase().includes(query))
      .map((row) => row.id);
  }

  const curated = new Set<string>(CLAUDE_PICKER_CURATED_IDS);
  const explicit = claudePickerExplicitVisibleModelSet(input.visibleExtraModelIds);
  explicit.forEach((id) => curated.add(id));
  const activeId = input.activeModelId.trim();
  if (activeId && activeId !== 'auto') {
    curated.add(activeId);
  }

  const available = new Set(models.map((row) => row.id));
  return [...curated].filter((id) => available.has(id));
}

export function claudePrimaryModelRows(input: {
  rows: ClaudeCatalogRow[];
  activeModelId: string;
  visibleExtraModelIds: string[];
}): ClaudeCatalogRow[] {
  if (isClaudeAutoModel(input.activeModelId)) {
    return [];
  }

  const ids = new Set(claudePrimaryDisplayIds(input));
  return claudeCatalogModelRows(input.rows).filter((row) => ids.has(row.id));
}

export function claudeManageModelRows(input: {
  rows: ClaudeCatalogRow[];
  searchQuery?: string;
}): ClaudeCatalogRow[] {
  const query = String(input.searchQuery ?? '').trim().toLowerCase();
  const rows = claudeCatalogModelRows(input.rows);
  if (!query) {
    return rows;
  }
  return rows.filter((row) =>
    `${row.label} ${row.id} ${row.description}`.toLowerCase().includes(query),
  );
}

export function claudeExtraModelRows(rows: ClaudeCatalogRow[]): ClaudeCatalogRow[] {
  return claudeCatalogModelRows(rows).filter((row) => !isClaudePickerCuratedModel(row.id));
}

export function claudePickerExtraModelSelected(
  modelId: string,
  visibleExtraModelIds: string[],
): boolean {
  const id = modelId.trim();
  if (!id || id === 'auto') {
    return false;
  }
  return claudePickerExplicitVisibleModelSet(visibleExtraModelIds).has(id);
}

export function claudeCatalogScopeLabel(visibleExtraModelIds: string[], searchQuery = ''): string {
  if (searchQuery.trim()) {
    return 'Search results';
  }
  if (claudePickerExplicitVisibleModelSet(visibleExtraModelIds).size) {
    return 'Claude defaults + selected';
  }
  return 'Claude defaults';
}

export function claudeCatalogCountLabel(input: {
  rows: ClaudeCatalogRow[];
  visibleExtraModelIds: string[];
  searchQuery?: string;
}): string {
  const shown = claudeManageModelRows({
    rows: input.rows,
    searchQuery: input.searchQuery,
  }).length;
  const total = claudeCatalogModelRows(input.rows).length;
  const scope = claudeCatalogScopeLabel(input.visibleExtraModelIds, input.searchQuery);
  return `${scope} · ${shown} shown · ${total} total`;
}

export function claudeCatalogStatusLabel(input: {
  loading: boolean;
  snapshot: ClaudeRuntimeStatusSnapshot | null;
}): string {
  if (input.loading) {
    return 'Refreshing Claude catalog';
  }
  return 'Claude catalog';
}

export function claudeStaleModelWarning(input: {
  modelId: string;
  rows: ClaudeCatalogRow[];
  snapshot: ClaudeRuntimeStatusSnapshot | null;
}): string {
  const id = input.modelId.trim();
  if (!id || id === 'auto') {
    return '';
  }
  const available = input.rows.some((row) => row.id === id && row.available !== false);
  if (available) {
    return '';
  }
  return `${id} is not in the Claude model catalog. Choose Auto or a listed model.`;
}

export function claudeModelLabel(modelId: string, rows: ClaudeCatalogRow[]): string {
  const normalized = modelId.trim();
  if (!normalized || normalized === 'auto') {
    return 'Auto';
  }
  return rows.find((row) => row.id === normalized)?.label ?? normalized;
}

/** Tooltip / detail line: `Claude · Sonnet` (not `claude local · Sonnet`). */
export function claudeRuntimeLabel(input: {
  family: string;
  modelId: string;
  rows: ClaudeCatalogRow[];
}): string {
  const family = composerRuntimeFamilyLabel(input.family);
  const normalized = input.modelId.trim();
  const modelLabel = claudeModelLabel(normalized || CLAUDE_PICKER_DEFAULT_MODEL, input.rows);
  return `${family} · ${modelLabel}`;
}

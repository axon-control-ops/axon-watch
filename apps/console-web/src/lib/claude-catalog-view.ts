import type { ClaudeRuntimeStatusSnapshot } from '../api/control-plane';

import { composerRuntimeFamilyLabel, type CursorCatalogRow } from './cursor-catalog-view';

/** Same row shape as CursorCatalogRow — reused rather than redefined. */
export type ClaudeCatalogRow = CursorCatalogRow;

/**
 * Claude's catalog is a fixed set of 4 aliases (Auto/Sonnet/Opus/Haiku) — unlike
 * Cursor's large, live-fetched catalog, there's nothing to browse, pin, or search.
 * This stays a flat list rather than mirroring Cursor's curated/pinned/manage tiers.
 */
export const CLAUDE_DEFAULT_MODEL = 'sonnet';

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
      : [{ id: 'auto', label: 'Auto', description: 'Let Claude Code choose automatically.' }],
  );

  return rows;
}

export function isClaudeAutoModel(modelId: string): boolean {
  const normalized = modelId.trim();
  return !normalized || normalized === 'auto';
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
  return CLAUDE_DEFAULT_MODEL;
}

export function claudeCatalogStatusLabel(input: { loading: boolean }): string {
  return input.loading ? 'Refreshing Claude catalog' : 'Claude catalog';
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
  const modelLabel = claudeModelLabel(normalized || CLAUDE_DEFAULT_MODEL, input.rows);
  return `${family} · ${modelLabel}`;
}

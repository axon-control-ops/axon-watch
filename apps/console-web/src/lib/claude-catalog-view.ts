import type { ClaudeRuntimeStatusSnapshot } from '../api/control-plane';

import { composerRuntimeFamilyLabel, type CursorCatalogRow } from './cursor-catalog-view';

/** Extends CursorCatalogRow with an optional effort level for Claude models. */
export type ClaudeCatalogRow = CursorCatalogRow & {
  effort?: string;
};

/**
 * Claude's catalog is a curated static list (Auto/Sonnet/Opus/Haiku × effort tiers).
 * Unlike Cursor there's no live `--list-models` discovery — the catalog comes from
 * the control plane's `claude_models.py` static list.
 */
export const CLAUDE_DEFAULT_MODEL = 'sonnet';

export function buildClaudeCatalogRows(
  snapshot: ClaudeRuntimeStatusSnapshot | null,
): ClaudeCatalogRow[] {
  const rows: ClaudeCatalogRow[] = [];
  const seen = new Set<string>();

  const add = (items: Array<{ id?: string; label?: string; description?: string; badge?: string; available?: boolean; effort?: string }>) => {
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
      const effort = String(item.effort ?? '').trim();
      if (effort) {
        row.effort = effort;
      }
      rows.push(row);
    }
  };

  const fallback = [
    { id: 'auto', label: 'Auto', description: 'Let Claude Code choose model and effort automatically.' },
    { id: 'sonnet', label: 'Sonnet', description: 'Balanced quality and speed — default.', badge: 'default', effort: 'medium' },
    { id: 'sonnet@low', label: 'Sonnet · Low', description: 'Reduced extended thinking — fastest responses.', effort: 'low' },
    { id: 'sonnet@high', label: 'Sonnet · High', description: 'Increased extended thinking — more thorough.', effort: 'high' },
    { id: 'sonnet@max', label: 'Sonnet · Max', description: 'Maximum extended thinking — most thorough, slowest.', effort: 'max' },
    { id: 'opus', label: 'Opus', description: 'Highest capability — deeper reasoning, slower.', effort: 'medium' },
    { id: 'opus@high', label: 'Opus · High', description: 'Opus with high extended thinking — complex problems.', effort: 'high' },
    { id: 'opus@max', label: 'Opus · Max', description: 'Opus with maximum extended thinking — hardest problems.', effort: 'max' },
    { id: 'haiku', label: 'Haiku', description: 'Fastest and most economical for lighter tasks.', effort: 'low' },
  ];

  add(snapshot?.available_models?.length ? snapshot.available_models : fallback);

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

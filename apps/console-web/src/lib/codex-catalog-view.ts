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
    const label = String(model.label ?? id).trim() || id;
    const description = String(model.description ?? 'Codex model available to this account.').trim();
    const defaultLevel = String(model.default_reasoning_level ?? '').trim().toLowerCase();
    const levels = Array.from(new Set((model.reasoning_levels ?? [])
      .map((level) => String(level).trim().toLowerCase())
      .filter(Boolean)));
    const orderedLevels = defaultLevel && levels.includes(defaultLevel)
      ? [defaultLevel, ...levels.filter((level) => level !== defaultLevel)]
      : levels;
    if (!orderedLevels.length) {
      rows.push({ id, label, description, ...(model.badge ? { badge: String(model.badge) } : {}), available: model.available !== false });
      continue;
    }
    for (const level of orderedLevels) {
      const isDefault = level === defaultLevel;
      rows.push({
        id: isDefault ? id : [id, level].join('@'),
        label: label + ' · ' + formatReasoningLevel(level),
        description: description + ' Reasoning: ' + formatReasoningLevel(level) + (isDefault ? ' (default).' : '.'),
        badge: formatReasoningLevel(level),
        defaultReasoningLevel: defaultLevel || undefined,
        reasoningLevels: orderedLevels,
        available: model.available !== false,
      });
    }
  }
  return rows;
}

function formatReasoningLevel(level: string): string {
  return level === 'xhigh' ? 'Extra high' : level.charAt(0).toUpperCase() + level.slice(1);
}

export function codexModelLabel(modelId: string, rows: CursorCatalogRow[]): string {
  const normalized = modelId.trim();
  if (!normalized || normalized === 'auto') {
    return rows.find((row) => row.available)?.label ?? 'Choose model';
  }
  return rows.find((row) => row.id === normalized)?.label ?? normalized;
}

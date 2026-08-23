/**
 * Detect when the operator's draft belongs in a different workspace than the
 * active IDE context (e.g. Young Eagles centre ops typed in DashPro).
 */

import { canonicalWorkspaceLabel, resolveWorkspaceIdFromPhrase } from './kairo-entity-labels';

export type ComposerWorkspaceScopeMismatch = {
  currentWorkspaceId: string;
  inferredWorkspaceId: string;
  currentLabel: string;
  inferredLabel: string;
  matchedHint: string;
};

const WORKSPACE_CONTENT_ALIASES: Record<string, string[]> = {
  workspace_young_eagles_day_care: [
    'young eagles',
    'young eagles day care',
    'young eagles daycare',
    'workspace_young_eagles_day_care',
    'teacher-x',
    'teacher x',
    'imani',
    'lesego',
    'dimakatso',
    'command-centre',
    'command centre',
  ],
  workspace_dashpro: [
    'dashpro',
    'dash pro',
    'edudash pro',
    'edudashpro',
    'workspace_dashpro',
    'expo ota',
    'eas update',
    'parent dashboard',
  ],
  workspace_edudashpro_school: [
    'edp excellence',
    'school of excellence',
    'workspace_edudashpro_school',
  ],
  workspace_axon_watch: ['axon watch', 'axon-watch', 'mission control', 'fast gate'],
  workspace_tps: ['tps workspace', 'workspace_tps'],
};

const YOUNG_EAGLES_PATTERNS: RegExp[] = [
  /\byoung eagles\b/i,
  /\bteacher[- ]?x\b/i,
  /\bimani\b/i,
  /\blesego\b/i,
  /\bdimakatso\b/i,
  /\bworkspace_young_eagles\b/i,
  /services\/ops\/[^\s]*(?:young|eagles|enrol)/i,
];

const DASHPRO_PATTERNS: RegExp[] = [
  /\bdashpro\b/i,
  /\bdash pro\b/i,
  /\bexpo\b.*\bota\b/i,
  /\beas update\b/i,
  /\bparent[- ]facing\b/i,
];

function normalizeContent(value: string): string {
  return value.trim().toLowerCase().replace(/[_\s-]+/g, ' ');
}

function aliasInContent(normalized: string, alias: string): boolean {
  const needle = alias.trim().toLowerCase().replace(/[_\s-]+/g, ' ');
  if (!needle || needle.length < 3) {
    return false;
  }
  return normalized.includes(needle);
}

/** Best-effort workspace inference from free-form composer text. */
export function inferWorkspaceIdsFromContent(
  content: string,
): Array<{ workspaceId: string; hint: string; weight: number }> {
  const trimmed = content.trim();
  if (!trimmed) {
    return [];
  }

  const normalized = normalizeContent(trimmed);
  const matches: Array<{ workspaceId: string; hint: string; weight: number }> = [];

  for (const [workspaceId, aliases] of Object.entries(WORKSPACE_CONTENT_ALIASES)) {
    for (const alias of aliases) {
      if (aliasInContent(normalized, alias)) {
        matches.push({ workspaceId, hint: alias, weight: alias.length });
      }
    }
  }

  for (const pattern of YOUNG_EAGLES_PATTERNS) {
    const hit = trimmed.match(pattern);
    if (hit) {
      matches.push({
        workspaceId: 'workspace_young_eagles_day_care',
        hint: hit[0],
        weight: hit[0].length + 4,
      });
    }
  }

  for (const pattern of DASHPRO_PATTERNS) {
    const hit = trimmed.match(pattern);
    if (hit) {
      matches.push({
        workspaceId: 'workspace_dashpro',
        hint: hit[0],
        weight: hit[0].length,
      });
    }
  }

  const phraseHit = resolveWorkspaceIdFromPhrase(trimmed);
  if (phraseHit) {
    matches.push({ workspaceId: phraseHit, hint: trimmed.slice(0, 40), weight: 40 });
  }

  const deduped = new Map<string, { workspaceId: string; hint: string; weight: number }>();
  for (const row of matches) {
    const existing = deduped.get(row.workspaceId);
    if (!existing || row.weight > existing.weight) {
      deduped.set(row.workspaceId, row);
    }
  }

  return [...deduped.values()].sort((left, right) => right.weight - left.weight);
}

export function resolveComposerWorkspaceScopeMismatch(
  currentWorkspaceId: string | null | undefined,
  draft: string,
): ComposerWorkspaceScopeMismatch | null {
  const current = String(currentWorkspaceId ?? '').trim();
  const text = draft.trim();
  if (!current || !text) {
    return null;
  }

  const inferred = inferWorkspaceIdsFromContent(text);
  const winner = inferred.find((row) => row.workspaceId !== current);
  if (!winner) {
    return null;
  }

  // A draft that's dominantly about the current workspace can still contain a
  // passing mention of another one (e.g. "consult Dana from DashPro" inside
  // Young-Eagles-scoped Instructions text). Only flag a mismatch when the
  // other workspace's strongest signal actually outweighs the current
  // workspace's own signal in the same draft — otherwise any bare keyword
  // mention, even a quoted/reference one, would false-positive.
  const currentWeight = inferred.find((row) => row.workspaceId === current)?.weight ?? 0;
  if (winner.weight <= currentWeight) {
    return null;
  }

  return {
    currentWorkspaceId: current,
    inferredWorkspaceId: winner.workspaceId,
    currentLabel: canonicalWorkspaceLabel(current),
    inferredLabel: canonicalWorkspaceLabel(winner.workspaceId),
    matchedHint: winner.hint,
  };
}

export function composerWorkspaceScopeBannerCopy(
  mismatch: ComposerWorkspaceScopeMismatch,
): string {
  return (
    `This looks like ${mismatch.inferredLabel} work, but you are in ${mismatch.currentLabel}. ` +
    'Switch workspace before sending so the right Lead and repo handle it.'
  );
}

import type { BrainGraphSnapshot } from './operator-brain-graph-view';
import { OPERATOR_PERSONA_NAME } from './operator-persona-name';
import { normalizePersonaSttAliases } from './operator-persona-stt-aliases';

const CANONICAL_WORKSPACE_LABELS: Record<string, string> = {
  workspace_axon_watch: 'Axon Watch',
  workspace_dashpro: 'DashPro',
  workspace_edudashpro_school: 'EDP Excellence',
  workspace_tps: 'TPS',
  workspace_young_eagles_day_care: 'Young Eagles Day Care',
};

const WORKSPACE_ID_ALIASES: Record<string, string> = {
  'axon watch': 'workspace_axon_watch',
  axonwatch: 'workspace_axon_watch',
  'axon-watch': 'workspace_axon_watch',
  watch: 'workspace_axon_watch',
  dashpro: 'workspace_dashpro',
  'dash pro': 'workspace_dashpro',
  'desk pro': 'workspace_dashpro',
  deskpro: 'workspace_dashpro',
  school: 'workspace_edudashpro_school',
  'school of excellence': 'workspace_edudashpro_school',
  'edudashpro school': 'workspace_edudashpro_school',
  'edu dash pro school': 'workspace_edudashpro_school',
  'edu pro': 'workspace_edudashpro_school',
  edupro: 'workspace_edudashpro_school',
  'edu-pro': 'workspace_edudashpro_school',
  'edudash pro': 'workspace_edudashpro_school',
  edudashpro: 'workspace_edudashpro_school',
  aftercare: 'workspace_edudashpro_school',
  preschool: 'workspace_edudashpro_school',
  'edp excellence': 'workspace_edudashpro_school',
  edpexcellence: 'workspace_edudashpro_school',
  tps: 'workspace_tps',
  'tps workspace': 'workspace_tps',
  'young eagles': 'workspace_young_eagles_day_care',
  'young eagles day care': 'workspace_young_eagles_day_care',
};

const VOICE_TRANSCRIPT_REPLACEMENTS: Array<[RegExp, string]> = [
  [/\bdesk\s*pro\b/gi, 'DashPro'],
  [/\bdash\s*pro\b/gi, 'DashPro'],
  [/\bdashpro\b/gi, 'DashPro'],
  [/\baxon\s*watch\b/gi, 'Axon Watch'],
  [/\baxon-watch\b/gi, 'Axon Watch'],
  [/\bschool\s+of\s+excellence\b/gi, 'EDP Excellence'],
  [/\bedudashpro\s+school\b/gi, 'EDP Excellence'],
  [/\bedp\s+excellence\b/gi, 'EDP Excellence'],
  [/\byoung\s+eagles(?:\s+day\s+care)?\b/gi, 'Young Eagles Day Care'],
  [/\btps\b/gi, 'TPS'],
];

function normalizeAliasKey(value: string): string {
  return value.trim().toLowerCase().replace(/[_\s-]+/g, ' ');
}

export function normalizeVoiceTranscript(text: string): string {
  let result = normalizePersonaSttAliases(text.trim());
  for (const [pattern, replacement] of VOICE_TRANSCRIPT_REPLACEMENTS) {
    result = result.replace(pattern, replacement);
  }
  return result;
}

export function normalizeKairoCopy(text: string): string {
  return normalizeVoiceTranscript(text);
}

export function canonicalWorkspaceLabel(
  workspaceId: string,
  displayName?: string | null,
): string {
  const canonical = CANONICAL_WORKSPACE_LABELS[workspaceId];
  if (canonical) {
    return canonical;
  }
  const raw = (displayName ?? workspaceId).trim();
  return normalizeEntityDisplayLabel(raw);
}

function normalizeEntityDisplayLabel(raw: string): string {
  const key = normalizeAliasKey(raw);
  if (key === 'dashpro' || key === 'dash pro' || key === 'desk pro') {
    return 'DashPro';
  }
  if (key === 'axon watch') {
    return 'Axon Watch';
  }
  if (key === 'kairo' || key === 'cairo' || key === 'x' || key === 'vaxon') {
    return OPERATOR_PERSONA_NAME;
  }
  return raw;
}

export function canonicalBrainGraphLabel(
  label: string,
  kind: string,
  workspaceId?: string | null,
): string {
  if (kind === 'core') {
    return OPERATOR_PERSONA_NAME;
  }
  if (kind === 'workspace') {
    if (workspaceId) {
      return canonicalWorkspaceLabel(workspaceId, label);
    }
    return normalizeEntityDisplayLabel(label);
  }
  return label;
}

export function normalizeBrainGraphSnapshot(snapshot: BrainGraphSnapshot): BrainGraphSnapshot {
  return {
    ...snapshot,
    nodes: snapshot.nodes.map((node) => ({
      ...node,
      label: canonicalBrainGraphLabel(node.label, node.kind, node.workspace_id),
    })),
  };
}

export function resolveWorkspaceIdFromPhrase(phrase: string): string | null {
  const normalized = normalizeAliasKey(phrase);
  const compact = normalized.replace(/\s+/g, '');
  return WORKSPACE_ID_ALIASES[normalized] ?? WORKSPACE_ID_ALIASES[compact] ?? null;
}

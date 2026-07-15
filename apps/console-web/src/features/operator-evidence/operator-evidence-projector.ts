import type { OperatorEvidenceRecord } from '../../api/operator-api';

const EVIDENCE_ICONS = ['doc', 'link', 'db', 'pulse', 'shield', 'mail'] as const;

export type EvidenceRowView = {
  id: string;
  title: string;
  detail: string;
  source: string;
  ago: string;
  icon: (typeof EVIDENCE_ICONS)[number];
};

export type EvidenceAutonomyStatus = {
  label: string;
  tone: 'nominal' | 'attention' | 'critical' | 'info';
};

export function evidenceKindLabel(kind: string | undefined): string {
  const value = kind ?? 'node';
  if (value === 'core') {
    return 'System Node';
  }
  return value.charAt(0).toUpperCase() + value.slice(1);
}

export function projectEvidenceRows(evidence: OperatorEvidenceRecord | null): EvidenceRowView[] {
  const rows: EvidenceRowView[] = [];
  const sections = evidence?.sections ?? [];
  if (sections.length) {
    for (const section of sections) {
      for (const item of section.items) {
        rows.push({
          id: `section:${section.title}:${item.title}`,
          title: item.title,
          detail: item.detail,
          source: item.source_ref?.label || section.title,
          ago: '',
          icon: EVIDENCE_ICONS[rows.length % EVIDENCE_ICONS.length] ?? 'doc',
        });
      }
    }
  } else {
    for (const fact of evidence?.facts ?? []) {
      rows.push({
        id: `fact:${fact.label}`,
        title: fact.label,
        detail: fact.value,
        source: 'Evidence',
        ago: '',
        icon: EVIDENCE_ICONS[rows.length % EVIDENCE_ICONS.length] ?? 'doc',
      });
    }
  }
  return rows.slice(0, 8);
}

export function projectEvidenceTags(
  evidence: OperatorEvidenceRecord | null,
  workspaceId: string,
): string[] {
  const kind = evidence?.kind;
  const next = [kind, workspaceId ? 'workspace' : null].filter(Boolean) as string[];
  if (kind === 'core') {
    return ['core', 'system', 'high_value', 'trusted'];
  }
  if (kind === 'signal') {
    next.push('attention');
  }
  return next.slice(0, 4);
}

export function projectEvidenceAutonomyStatus(input: {
  pendingApprovals: number;
  runPhase: string | null;
  /** Last converse action_tier from live KAIRO policy, when known. */
  actionTier?: string | null;
  /** @deprecated Prefer actionTier; kept for older callers. */
  autoAllowed?: boolean;
}): EvidenceAutonomyStatus {
  if (input.pendingApprovals > 0) {
    return { label: 'Approval gated', tone: 'critical' };
  }
  if (input.runPhase === 'awaiting_approval' || input.runPhase === 'review_ready') {
    return { label: `Run · ${input.runPhase.replace('_', ' ')}`, tone: 'attention' };
  }
  const tier = (input.actionTier || '').trim();
  if (tier === 'reversible_auto') {
    return { label: 'Bounded auto', tone: 'info' };
  }
  if (tier === 'approval_gated') {
    return { label: 'Approval gated', tone: 'attention' };
  }
  if (tier === 'unsupported') {
    return { label: 'Unsupported', tone: 'attention' };
  }
  if (input.autoAllowed === true) {
    return { label: 'Bounded auto', tone: 'info' };
  }
  return { label: 'Manual', tone: 'nominal' };
}

export function projectEmailTriageHandoffMeta(
  evidence: OperatorEvidenceRecord | null,
): Record<string, unknown> | null {
  const facts = evidence?.facts ?? [];
  const factValue = (label: string): string =>
    facts.find((fact) => fact.label === label)?.value?.trim() ?? '';
  const family = factValue('Family');
  if (family !== 'email_triage') {
    return null;
  }
  return {
    signal_family: family,
    sender: factValue('Sender'),
    subject: factValue('Subject'),
    recommended_action: factValue('Recommended action'),
    recommended_detail: evidence?.summary ?? '',
  };
}

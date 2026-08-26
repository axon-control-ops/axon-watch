/** Lead team-health check-in — readable card + next steps + operator options. */

import type { AgentQuestionOption } from './agent-question-view';

/** Mirrors recovery_decision.py's CardType — do not blur these. */
export type RecoveryCardType =
  | 'working'
  | 'recovered'
  | 'blocked'
  | 'decision_required'
  | 'completed'
  | 'failed';

export type RecoveryChoiceView = {
  id: string;
  label: string;
  expectedResult: string;
  risk: string;
  recommended: boolean;
  isPause: boolean;
};

export type RecoveryEvidenceView = { label: string; ref: string };

/** Frontend mirror of recovery_decision.py's RecoveryDecision.to_payload() —
 * the backend decides the card shape, this just carries it through unchanged. */
export type RecoveryDecisionView = {
  cardType: RecoveryCardType;
  summary: string;
  classification: string;
  operatorActionRequired: boolean;
  recommendedAction: string;
  automaticNextAction: string | null;
  actionsAttempted: string[];
  evidence: RecoveryEvidenceView[];
  confidence: number;
  retryEligible: boolean;
  recoveryEligible: boolean;
  escalationReason: string | null;
  choices: RecoveryChoiceView[];
};

export type LeadCheckinFindingView = {
  kind: string;
  kindLabel: string;
  title: string;
  owner: string;
  escalate: boolean;
  summary: string;
  detail: string;
  decision?: RecoveryDecisionView;
};

export type LeadCheckinCard = {
  title: string;
  summary: string;
  findingCount: number;
  assignmentCount: number;
  findings: LeadCheckinFindingView[];
  nextSteps: string[];
  prompt: string;
  options: AgentQuestionOption[];
};

const CHECKIN_HEAD_RE = /^Lead check-in:\s*(.+)$/i;
const COUNTS_RE = /Findings:\s*(\d+)\s*[·•|]\s*Assignments created:\s*(\d+)/i;
const FINDING_RE =
  /^\s*(\d+)\.\s*\[([^\]]+)\]\s+(.+)\s+\((ESCALATE|→\s*[^)]+)\)\s*$/i;
const KIND_LABELS: Record<string, string> = {
  failed_shift: 'Failed shift',
  operator_blocker: 'Needs you',
  monitor_alert: 'Monitor',
  connector_degraded: 'Connector',
  critical_signal: 'Critical',
  warning_signal: 'Warning',
  open_handoff: 'Handoff',
};

export const LEAD_CHECKIN_PROMPT = 'How should the Lead handle this team health pass?';

export function looksLikeLeadCheckinReport(text: string): boolean {
  const trimmed = String(text || '').trim();
  if (!trimmed) {
    return false;
  }
  return CHECKIN_HEAD_RE.test(trimmed.split('\n')[0] ?? '');
}

export function humanizeLeadFailureDetail(detail: string): string {
  const raw = String(detail || '').replace(/\s+/g, ' ').trim();
  if (!raw) {
    return 'No extra detail.';
  }
  const lowered = raw.toLowerCase();
  if (/out of usage|increase limits/.test(lowered)) {
    return 'Cursor usage is exhausted. Raise the limit, then retry this shift.';
  }
  if (/unpaid invoice|credit balance|billing/.test(lowered)) {
    return 'Billing is blocking this shift. Clear the invoice, then retry.';
  }
  if (/not signed in|authentication|api_key_invalid|auth probe/.test(lowered)) {
    return 'The agent runtime is not signed in. Unlock auth, then retry.';
  }
  const outOfScope = /out_of_scope|out of scope/.test(lowered);
  const gate6 = /gate 6|acceptance_evidence|acceptance evidence/.test(lowered);
  if (gate6 && outOfScope) {
    return 'Delivery was blocked: acceptance did not pass (Gate 6) because the change was marked out of scope.';
  }
  if (gate6) {
    return 'Delivery was blocked: acceptance evidence did not pass (Gate 6).';
  }
  if (/lane b finalization failed/.test(lowered)) {
    const inner = raw.replace(/^Lane B finalization failed:\s*/i, '').trim();
    return inner ? humanizeLeadFailureDetail(inner) : 'The shift could not finish delivery.';
  }
  return raw
    .replace(/\s*\[[^\]]*run[^\]]*\]\s*$/i, '')
    .replace(/\s*\|\s*acceptance=fail[^.]*$/i, '')
    .trim();
}

function kindLabel(kind: string): string {
  return KIND_LABELS[kind.trim().toLowerCase()] ?? kind.replace(/_/g, ' ');
}

function parseRecoveryDecisionFence(body: string): RecoveryDecisionView | undefined {
  try {
    const payload = JSON.parse(body) as Record<string, unknown>;
    const choices = Array.isArray(payload.choices) ? payload.choices : [];
    const evidence = Array.isArray(payload.evidence) ? payload.evidence : [];
    return {
      cardType: (String(payload.card_type || 'blocked')) as RecoveryCardType,
      summary: String(payload.summary || ''),
      classification: String(payload.classification || ''),
      operatorActionRequired: Boolean(payload.operator_action_required),
      recommendedAction: String(payload.recommended_action || ''),
      automaticNextAction:
        payload.automatic_next_action == null ? null : String(payload.automatic_next_action),
      actionsAttempted: Array.isArray(payload.actions_attempted)
        ? payload.actions_attempted.map((item) => String(item))
        : [],
      evidence: evidence
        .filter((item): item is Record<string, unknown> => !!item && typeof item === 'object')
        .map((item) => ({ label: String(item.label || ''), ref: String(item.ref || '') })),
      confidence: Number(payload.confidence ?? 0.5),
      retryEligible: Boolean(payload.retry_eligible),
      recoveryEligible: Boolean(payload.recovery_eligible),
      escalationReason:
        payload.escalation_reason == null ? null : String(payload.escalation_reason),
      choices: choices
        .filter((item): item is Record<string, unknown> => !!item && typeof item === 'object')
        .map((item) => ({
          id: String(item.id || ''),
          label: String(item.label || ''),
          expectedResult: String(item.expected_result || ''),
          risk: String(item.risk || ''),
          recommended: Boolean(item.recommended),
          isPause: Boolean(item.is_pause),
        })),
    };
  } catch {
    // Malformed fence (truncated stream, corrupted history) — fall back to
    // the legacy prose-derived options rather than crash the transcript.
    return undefined;
  }
}

function parseFindingBlock(lines: string[]): LeadCheckinFindingView[] {
  const findings: LeadCheckinFindingView[] = [];
  let index = 0;
  while (index < lines.length) {
    const line = lines[index];
    const match = line.match(FINDING_RE);
    if (match) {
      const kind = (match[2] || '').trim().toLowerCase();
      const title = (match[3] || '').trim();
      const flag = (match[4] || '').trim();
      const escalate = /^escalate$/i.test(flag);
      const owner = escalate ? '' : flag.replace(/^→\s*/, '').trim();
      findings.push({
        kind,
        kindLabel: kindLabel(kind),
        title,
        owner,
        escalate,
        summary: title,
        detail: '',
      });
      index += 1;
      continue;
    }
    if (line.trimEnd() === ':::decision') {
      const body: string[] = [];
      index += 1;
      while (index < lines.length && lines[index].trimEnd() !== ':::') {
        body.push(lines[index]);
        index += 1;
      }
      if (index < lines.length) {
        index += 1; // consume the closing ':::'
      }
      const last = findings[findings.length - 1];
      if (last) {
        last.decision = parseRecoveryDecisionFence(body.join('\n'));
      }
      continue;
    }
    const last = findings[findings.length - 1];
    if (last && /^\s+\S/.test(line)) {
      const extra = line.trim();
      last.detail = last.detail ? `${last.detail} ${extra}` : extra;
    }
    index += 1;
  }
  return findings.map((finding) => ({
    ...finding,
    detail: humanizeLeadFailureDetail(finding.detail),
  }));
}

function nextStepsFor(findings: LeadCheckinFindingView[]): string[] {
  if (!findings.length) {
    return ['No failed shifts or degraded signals this pass. Keep the team on the current work.'];
  }
  const steps: string[] = [];
  for (const finding of findings.slice(0, 4)) {
    if (finding.decision) {
      // The control plane already inspected and decided — surface its actual
      // recommendation instead of re-guessing one from the finding's flags.
      const action = finding.decision.automaticNextAction || finding.decision.recommendedAction;
      steps.push(action ? `${finding.title}: ${action}` : `Review ${finding.title}.`);
      continue;
    }
    if (finding.escalate) {
      steps.push(`Unblock ${finding.title} — this needs an operator gate, not another auto-retry.`);
      continue;
    }
    if (finding.kind === 'failed_shift') {
      steps.push(`Inspect ${finding.title}, then retry only if the acceptance/scope issue is fixed.`);
      continue;
    }
    steps.push(`Have ${finding.owner || 'the specialist'} investigate: ${finding.title}.`);
  }
  steps.push('Use Recovery Center if the run is stale, not a destructive Clear.');
  return steps.slice(0, 5);
}

function retryLabel(finding: LeadCheckinFindingView): string {
  const name = finding.title.replace(/\s*\([^)]+\)\s*last shift failed$/i, '').trim();
  const role = finding.title.match(/\(([^)]+)\)\s*last shift failed$/i)?.[1]?.trim();
  if (name && role) {
    return `Retry ${name}'s ${role} shift`;
  }
  return `Retry ${finding.title}`;
}

function optionsFor(findings: LeadCheckinFindingView[]): AgentQuestionOption[] {
  // An all-clear check-in is informational, not an approval or recovery
  // decision.  Offering retry/recovery choices without a finding invites the
  // operator to act on stale or unrelated state.
  if (!findings.length) {
    return [];
  }
  const primary = findings[0];
  if (primary?.decision) {
    // The control plane already diagnosed and decided the card shape — only
    // decision_required carries a real fork with competing options. Every
    // other card type (working/recovered/blocked/completed/failed) is a
    // single outcome or a single missing requirement, not a menu to invent.
    if (primary.decision.cardType !== 'decision_required') {
      return [];
    }
    return primary.decision.choices.map((choice) => ({ id: choice.id, label: choice.label }));
  }
  // Legacy fallback: prose-only history predating the structured fence.
  const options: AgentQuestionOption[] = [];
  if (primary && !primary.escalate && primary.kind === 'failed_shift') {
    options.push({ id: '1', label: retryLabel(primary) });
  } else if (primary?.escalate) {
    options.push({ id: '1', label: 'Fix the operator blocker, then retry' });
  } else if (primary) {
    options.push({ id: '1', label: `Assign ${primary.owner || 'specialist'} to investigate` });
  }
  options.push({ id: String(options.length + 1), label: 'Inspect the failed run / evidence' });
  options.push({ id: String(options.length + 1), label: 'Open Recovery Center' });
  options.push({ id: String(options.length + 1), label: "Hold — I'll decide" });
  return options.slice(0, 5);
}

function promptFor(findings: LeadCheckinFindingView[]): string {
  const primary = findings[0];
  if (primary?.decision?.cardType === 'decision_required') {
    return primary.decision.summary || LEAD_CHECKIN_PROMPT;
  }
  return LEAD_CHECKIN_PROMPT;
}

export function parseLeadCheckinReport(text: string): LeadCheckinCard | null {
  const trimmed = String(text || '').trim();
  if (!looksLikeLeadCheckinReport(trimmed)) {
    return null;
  }
  const lines = trimmed.split('\n');
  const head = lines[0]?.match(CHECKIN_HEAD_RE)?.[1]?.trim() || 'team health pass';
  const countLine = lines.find((line) => COUNTS_RE.test(line)) ?? '';
  const counts = countLine.match(COUNTS_RE);
  const findingCount = counts ? Number(counts[1]) : 0;
  const assignmentCount = counts ? Number(counts[2]) : 0;
  const findings = parseFindingBlock(lines.slice(1));
  const nextSteps = nextStepsFor(findings);
  const summary =
    findings.length === 0
      ? 'All clear this pass.'
      : `${findings.length} finding${findings.length === 1 ? '' : 's'} · ${assignmentCount} assignment${
          assignmentCount === 1 ? '' : 's'
        } created`;
  return {
    title: head.replace(/\.$/, ''),
    summary,
    findingCount: findings.length || findingCount,
    assignmentCount,
    findings,
    nextSteps,
    prompt: promptFor(findings),
    options: optionsFor(findings),
  };
}

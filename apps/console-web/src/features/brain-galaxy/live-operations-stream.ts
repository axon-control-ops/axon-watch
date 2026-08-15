import type {
  CompanyEmployeeRecord,
  OperatorBriefing,
  RunRecord,
} from '../../contracts/canonical';
import { employeeFailureLine } from '../workspace-agents/company-roster-view';
import { getKairoVoiceUtteranceState } from '../../lib/kairo-voice-utterance';
import type { GalaxyPresencePhase } from './galaxy-presence-state';

export type LiveOperationsAutonomyReceipt = {
  receipt_id?: string;
  kind?: string;
  decision?: string;
  title?: string;
  detail?: string;
  ask_operator?: boolean;
  status?: string;
  resolution?: string;
  risk?: string;
  created_at?: string;
  payload?: Record<string, unknown>;
};

export type LiveOperationsStreamItem = {
  id: string;
  text: string;
  tone: 'nominal' | 'attention' | 'critical' | 'info';
  kind: 'spoken' | 'signal' | 'run' | 'employee' | 'connectivity' | 'routing' | 'autonomy';
  agent: string;
  at: string;
};

function truncate(text: string, max = 96): string {
  const trimmed = text.trim().replace(/\s+/g, ' ');
  if (trimmed.length <= max) {
    return trimmed;
  }
  return `${trimmed.slice(0, max - 1).trimEnd()}…`;
}

function clockStamp(date = new Date()): string {
  const hh = String(date.getHours()).padStart(2, '0');
  const mm = String(date.getMinutes()).padStart(2, '0');
  const ss = String(date.getSeconds()).padStart(2, '0');
  return `${hh}:${mm}:${ss}`;
}

function pushItem(
  items: LiveOperationsStreamItem[],
  item: Omit<LiveOperationsStreamItem, 'at'> & { at?: string },
): void {
  items.push({
    ...item,
    at: item.at ?? clockStamp(),
  });
}

/**
 * Strips raw backend identifiers and translates signal titles into plain English
 * that an operator can act on without knowing internal run IDs or branch names.
 *
 * Examples:
 *   "Docs Policy Enforcement still red on worker/run_1071031bf1cd"
 *     → "Policy check failing — talk to Soren (Integrations)"
 *   "Inspect Android CI/CD Pipeline failed on feature/chat-pop-ingest"
 *     → "Android CI failing — ask Soren to investigate"
 *   "Lead reviews are ready in Mission Control — Six of them"
 *     → (unchanged, already readable)
 */
export function humanizeSignalTitle(raw: string): string {
  if (!raw) return raw;

  let text = raw.trim();

  // Strip run IDs: worker/run_<hex>, run/<hex>, etc.
  text = text.replace(/\bworker\/run_[a-f0-9]+\b/gi, '').trim();
  text = text.replace(/\brun\/[a-f0-9]+\b/gi, '').trim();
  // Strip branch names: feature/<slug>, fix/<slug>, chore/<slug>
  text = text.replace(/\b(feature|fix|chore|hotfix|release)\/[\w\-.]+\b/gi, (m) => {
    // Keep just the human part after the prefix for readability
    const slug = m.replace(/^[^/]+\//, '').replace(/[-_]/g, ' ');
    return slug;
  });
  // Normalise trailing noise after stripping IDs
  text = text.replace(/\s+(still\s+)?on\s*$/i, '').trim();
  text = text.replace(/\s+/g, ' ').replace(/\s*—\s*$/, '').trim();

  // Translate known policy / check patterns
  const lower = text.toLowerCase();

  if (/docs\s*policy/i.test(text) && /red|fail|still/i.test(text)) {
    return 'Policy check failing — talk to Soren (Integrations) to resolve';
  }
  if (/android\s*(ci|cd|pipeline)/i.test(text) && /fail/i.test(text)) {
    return `Android CI failing${extractBranchHint(raw)} — ask Soren to investigate`;
  }
  if (/ci\/cd.*fail/i.test(text) || /pipeline.*fail/i.test(text)) {
    const pipeline = text.match(/^[\w\s]+ Pipeline/i)?.[0] ?? 'Pipeline';
    return `${pipeline} failing${extractBranchHint(raw)} — ask Soren to investigate`;
  }
  if (/deploy.*fail/i.test(text)) {
    return 'Deployment failing — check with Soren (Integrations)';
  }
  if (/policy.*red|red.*policy/i.test(lower)) {
    return 'Policy check still failing — talk to Soren to fix';
  }
  if (/test.*fail|fail.*test/i.test(lower)) {
    return `Tests failing${extractBranchHint(raw)} — ask the relevant specialist`;
  }
  if (/lead.*review.*ready|review.*ready/i.test(lower)) {
    // Already readable, just clean up
    return text;
  }

  return text;
}

function extractBranchHint(raw: string): string {
  const m = raw.match(/\b(feature|fix|chore|hotfix|release)\/([\w\-.]+)\b/i);
  if (!m) return '';
  const name = m[2]!.replace(/[-_]/g, ' ');
  return ` on "${name}"`;
}

function normalizeStreamText(text: string): string {
  return text
    .trim()
    .toLowerCase()
    .replace(/\s+/g, ' ')
    .replace(/[.…]+$/g, '')
    .replace(/^(inspect|review|check)\s+/i, '')
    .replace(/\.$/, '');
}

function streamTextsNearDuplicate(left: string, right: string): boolean {
  const a = normalizeStreamText(left);
  const b = normalizeStreamText(right);
  if (!a || !b) {
    return false;
  }
  if (a === b) {
    return true;
  }
  // Truncated spoken vs advise often share a long prefix but not full containment.
  const prefixLen = 40;
  if (a.length >= prefixLen && b.length >= prefixLen && a.slice(0, prefixLen) === b.slice(0, prefixLen)) {
    return true;
  }
  const shorter = a.length <= b.length ? a : b;
  const longer = a.length <= b.length ? b : a;
  return shorter.length >= 24 && longer.includes(shorter);
}

/** Prefer the richer line when spoken/notice/advise/signal overlap. */
export function collapseNearDuplicateStreamItems(
  items: LiveOperationsStreamItem[],
): LiveOperationsStreamItem[] {
  const out: LiveOperationsStreamItem[] = [];
  for (const item of items) {
    const matchIndex = out.findIndex((existing) =>
      streamTextsNearDuplicate(existing.text, item.text),
    );
    if (matchIndex < 0) {
      out.push(item);
      continue;
    }
    const existing = out[matchIndex]!;
    if (item.text.trim().length > existing.text.trim().length) {
      out[matchIndex] = item;
    }
  }
  return out;
}

/** Compact mission ticker for the LIVE OPERATIONS orb card. */
export function projectLiveOperationsStream(input: {
  briefing: OperatorBriefing | null;
  primaryActiveRun: RunRecord | null;
  employees?: CompanyEmployeeRecord[] | null;
  presencePhase: GalaxyPresencePhase;
  routingReceipt?: string | null;
  degradedReasons?: string[];
  autonomyReceipts?: LiveOperationsAutonomyReceipt[] | null;
  autonomyMode?: string | null;
  now?: Date;
}): LiveOperationsStreamItem[] {
  const stamp = clockStamp(input.now ?? new Date());
  const items: LiveOperationsStreamItem[] = [];
  const utterance = getKairoVoiceUtteranceState().text?.trim();
  if (utterance) {
    pushItem(items, {
      id: 'spoken',
      text: truncate(utterance, 140),
      tone: 'info',
      kind: 'spoken',
      agent: 'VAXON',
      at: stamp,
    });
  }

  const mode = String(input.autonomyMode || '').trim().toLowerCase();
  if (mode === 'full' && input.presencePhase === 'autonomous') {
    pushItem(items, {
      id: 'autonomy-mode',
      text: 'AUTONOMOUS ON · attending Mission Control',
      tone: 'info',
      kind: 'autonomy',
      agent: 'VAXON',
      at: stamp,
    });
  }

  for (const receipt of (input.autonomyReceipts ?? []).slice(0, 4)) {
    const title = String(receipt.title || receipt.detail || receipt.kind || '').trim();
    if (!title) {
      continue;
    }
    const ask =
      Boolean(receipt.ask_operator) &&
      String(receipt.status || 'pending').toLowerCase() === 'pending';
    const decision = String(receipt.decision || '').trim().toLowerCase();
    const resolution = String(receipt.resolution || '').trim().toLowerCase();
    const taskStatus = String(receipt.payload?.task_status || '').trim().toLowerCase();
    const createdAt = new Date(String(receipt.created_at || ''));
    const receiptStamp = Number.isNaN(createdAt.getTime()) ? stamp : clockStamp(createdAt);
    pushItem(items, {
      id: `auton-${receipt.receipt_id || title}`,
      text: truncate(
        ask
          ? `Needs you · ${title}`
          : resolution === 'approved'
            ? `Approved · ${title}`
            : resolution === 'rejected'
              ? `Rejected · ${title}`
          : taskStatus === 'completed'
            ? `Completed · ${title}`
            : taskStatus === 'failed' || taskStatus === 'cancelled'
              ? `${taskStatus === 'failed' ? 'Failed' : 'Cancelled'} · ${title}`
          : decision === 'dispatch'
            ? `Dispatched · ${title}`
            : decision === 'escalate'
              ? `Escalated · ${title}`
              : title,
      ),
      tone:
        ask || String(receipt.risk || '').toLowerCase() === 'critical'
          ? 'critical'
          : resolution === 'approved'
            ? 'info'
            : resolution === 'rejected'
              ? 'nominal'
          : taskStatus === 'completed'
            ? 'nominal'
            : taskStatus === 'failed' || taskStatus === 'cancelled'
              ? 'attention'
          : decision === 'dispatch'
            ? 'info'
            : 'attention',
      kind: 'autonomy',
      agent: 'VAXON',
      at: receiptStamp,
    });
  }

  const notice = input.briefing?.notice?.trim();
  if (notice && !(utterance && streamTextsNearDuplicate(utterance, notice))) {
    pushItem(items, {
      id: 'notice',
      text: truncate(humanizeSignalTitle(notice)),
      tone: 'attention',
      kind: 'signal',
      agent: 'OPS',
      at: stamp,
    });
  }
  const advise = input.briefing?.advise?.trim();
  if (advise && !(utterance && streamTextsNearDuplicate(utterance, advise))) {
    pushItem(items, {
      id: 'advise',
      text: truncate(humanizeSignalTitle(advise)),
      tone: 'attention',
      kind: 'signal',
      agent: 'OPS',
      at: stamp,
    });
  }

  for (const signal of input.briefing?.top_signals?.slice(0, 2) ?? []) {
    const title = String(signal.title || '').trim();
    if (!title) {
      continue;
    }
    const severity = String(signal.severity || '').toLowerCase();
    pushItem(items, {
      id: `signal-${signal.signal_id || title}`,
      text: truncate(humanizeSignalTitle(title)),
      tone: severity === 'critical' ? 'critical' : severity === 'high' ? 'attention' : 'info',
      kind: 'signal',
      agent: 'SENTRY',
      at: stamp,
    });
  }

  const run = input.primaryActiveRun;
  if (run) {
    const summary = String(run.summary || run.phase || 'active run').trim();
    pushItem(items, {
      id: `run-${run.run_id}`,
      text: truncate(`Run · ${run.phase}: ${summary}`),
      tone: run.phase === 'executing' ? 'info' : 'nominal',
      kind: 'run',
      agent: 'CI',
      at: stamp,
    });
  }

  for (const employee of (input.employees ?? []).slice(0, 4)) {
    const name = String(employee.name || employee.role || '').trim();
    if (!name) {
      continue;
    }
    const agent = name.split(/\s+/)[0]?.toUpperCase() || 'TEAM';
    const failureLine = employeeFailureLine(employee);
    if (failureLine) {
      pushItem(items, {
        id: `emp-fail-${employee.employee_id}`,
        text: truncate(failureLine),
        tone: 'critical',
        kind: 'employee',
        agent,
        at: stamp,
      });
      continue;
    }
    if (
      employee.status === 'watching' ||
      employee.status === 'executing' ||
      employee.status === 'planning' ||
      employee.status === 'assigned'
    ) {
      pushItem(items, {
        id: `emp-${employee.employee_id}`,
        text: truncate(`${employee.status}`),
        tone: 'nominal',
        kind: 'employee',
        agent,
        at: stamp,
      });
    }
  }

  for (const reason of (input.degradedReasons ?? []).slice(0, 1)) {
    const text = reason.trim();
    if (text) {
      pushItem(items, {
        id: `degraded-${text.slice(0, 24)}`,
        text: truncate(text),
        tone: 'attention',
        kind: 'connectivity',
        agent: 'INTEL',
        at: stamp,
      });
    }
  }

  const receipt = input.routingReceipt?.trim();
  if (receipt) {
    pushItem(items, {
      id: 'routing',
      text: truncate(receipt),
      tone: 'info',
      kind: 'routing',
      agent: 'OPS',
      at: stamp,
    });
  }

  if (items.length === 0) {
    pushItem(items, {
      id: 'standby',
      text:
        input.presencePhase === 'listening'
          ? 'Listening…'
          : 'Watch connected · systems on standby',
      tone: 'nominal',
      kind: 'connectivity',
      agent: 'VAXON',
      at: stamp,
    });
  }

  // Collapse exact + nested near-duplicates (spoken often wraps notice/advise).
  const deduped = collapseNearDuplicateStreamItems(items);
  const limited = deduped.slice(0, 8);


  return limited;
}

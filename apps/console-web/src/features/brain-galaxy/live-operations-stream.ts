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
  if (notice) {
    pushItem(items, {
      id: 'notice',
      text: truncate(notice),
      tone: 'attention',
      kind: 'signal',
      agent: 'OPS',
      at: stamp,
    });
  }
  const advise = input.briefing?.advise?.trim();
  if (advise) {
    pushItem(items, {
      id: 'advise',
      text: truncate(advise),
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
      text: truncate(title),
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

  return items.slice(0, 8);
}

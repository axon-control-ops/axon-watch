import type { BriefingAction } from '../../contracts/canonical';
import type { InboxItem } from '../../contracts/canonical';
import { briefingActionCtaLabel } from '../../lib/briefing-action-executor';

export interface ReportTheaterDirective {
  id: string;
  /** First-person VAXON button label. */
  label: string;
  /** Supporting line under the primary directive. */
  detail: string;
  kind: 'primary' | 'secondary';
  briefingAction: BriefingAction | null;
  /** When true, VAXON executes this after speaking the commitment — no click required. */
  autoExecute: boolean;
}

type ReportWorkspace = {
  workspace_id: string;
  display_name?: string | null;
};

const FILLER_LINE_RE =
  /^(?:nothing screaming\.?|idle\.?|none verified yet\.?|fleet telemetry quiet\.?|listening for the briefing…?|lead standing by on the board\.?)$/i;

export function isReportTheaterFillerLine(line: string): boolean {
  return FILLER_LINE_RE.test(String(line || '').trim());
}

/** Rewrite operator-facing advise into what VAXON will do. */
export function toVaxonDirectiveLine(nextMove: string): string {
  const cleaned = String(nextMove || '')
    .trim()
    .replace(/\s+/g, ' ')
    .replace(/\.+$/, '');
  if (!cleaned) {
    return "I'll keep watching the fleet and brief you when something moves.";
  }
  if (/^I(?:'d|'ll| will)\b/i.test(cleaned)) {
    return `${cleaned.replace(
      /and review that signal next$/i,
      'and start that investigation next',
    )}.`;
  }
  if (/vaxon is attending/i.test(cleaned)) {
    return cleaned.endsWith('.') ? cleaned : `${cleaned}.`;
  }
  if (/needs review|need review/i.test(cleaned) && /switch/i.test(cleaned)) {
    return `I'll attend that workspace and start the investigation next.`;
  }
  if (/github/i.test(cleaned) && (/vault/i.test(cleaned) || /token/i.test(cleaned))) {
    return "I'll open Vault and restore the GitHub probe token next.";
  }
  if (/push did not|retry the push|lead receipt|branch protection/i.test(cleaned)) {
    return (
      "I'll open the Lead receipt, fix remote auth or branch protection, then retry the push."
    );
  }
  if (/open (?:the )?lead/i.test(cleaned) || /lead rollup/i.test(cleaned)) {
    return `I'll open the Lead rollup and walk the next handoff with you.`;
  }
  if (/approval/i.test(cleaned)) {
    return `I'll take us to Approvals and clear the gate before new work starts.`;
  }
  if (/^I'll\b/i.test(cleaned) && /tunnel/i.test(cleaned)) {
    return cleaned.endsWith('.') ? cleaned : `${cleaned}.`;
  }
  if (/tunnel|remote ingress|public health/i.test(cleaned)) {
    return "I'll restart the public tunnel next.";
  }
  if (/^inspect\s+/i.test(cleaned)) {
    return `I'll open Attention for ${cleaned.replace(/^inspect\s+/i, '').trim()}.`;
  }
  if (/sentry|signal|attention/i.test(cleaned) && !/^I'll\b/i.test(cleaned)) {
    return `I'll open Attention for ${cleaned}.`;
  }
  return `I'll open Attention for ${cleaned}.`;
}

export function toVaxonActionLabel(action: BriefingAction): string {
  if (action.kind === 'review_signal') {
    const title = action.title?.trim() || 'that signal';
    if (/^review\b/i.test(title)) {
      return `I'll switch us there and review that signal next`;
    }
    return `I'll open Attention for ${title}`;
  }
  if (action.kind === 'approve_run' || action.kind === 'resume_run') {
    return `I'll open Mission Control for that run`;
  }
  if (action.kind === 'inspect_runtime') {
    if (action.action_id === 'theater_start_tunnel' || /tunnel/i.test(action.title)) {
      return "I'll restart the public tunnel next";
    }
    return action.action_id === 'theater_open_vault' || /^open vault$/i.test(action.title)
      ? "I'll open Vault and restore runtime next"
      : `I'll open the command seam and inspect runtime`;
  }
  const fallback = briefingActionCtaLabel(action);
  if (/^I(?:'ll| will)\b/i.test(fallback)) {
    return fallback;
  }
  return `I'll ${fallback.charAt(0).toLowerCase()}${fallback.slice(1)}`;
}

export function synthesizeActionsFromSignals(
  signals: Array<Pick<InboxItem, 'signal_id' | 'title' | 'summary' | 'workspace_id'> | null | undefined>,
): BriefingAction[] {
  const out: BriefingAction[] = [];
  for (const signal of signals) {
    if (!signal) {
      continue;
    }
    const signalId = String(signal.signal_id || '').trim();
    if (!signalId) {
      continue;
    }
    out.push({
      action_id: `theater_review_${signalId}`,
      kind: 'review_signal',
      title: String(signal.title || 'top signal').trim() || 'top signal',
      detail: String(signal.summary || '').trim() || 'Open Attention on this signal.',
      workspace_id: signal.workspace_id ?? null,
      run_id: null,
      signal_id: signalId,
    });
  }
  return out;
}

/** Bind the primary CTA to the action that matches the spoken next move. */
export function matchActionForNextMove(
  nextMove: string,
  actions: BriefingAction[],
): BriefingAction | null {
  if (!actions.length) {
    return null;
  }
  const hay = nextMove.toLowerCase();
  // A Lead receipt is a promise to inspect evidence, not permission to run an
  // unrelated signal / approval action. Keep it visible but operator-triggered
  // until a dedicated receipt action exists.
  if (/lead receipt|push did not|retry(?:ing)? the push|exact push error/i.test(hay)) {
    return null;
  }
  const workspaceMatched = actions.find((action) => {
    const workspace = String(action.workspace_id || '')
      .trim()
      .toLowerCase()
      .replace(/^workspace[_-]/, '')
      .replace(/_/g, '-');
    return action.kind === 'review_signal' && workspace.length > 2 && hay.includes(workspace);
  });
  if (workspaceMatched) {
    return workspaceMatched;
  }
  const titled = actions.find((action) => {
    if (action.kind !== 'review_signal') {
      return false;
    }
    const title = String(action.title || '').trim().toLowerCase();
    if (!title || /^review\b/i.test(title)) {
      return false;
    }
    return hay.includes(title.slice(0, Math.min(title.length, 24)));
  });
  if (titled) {
    return titled;
  }
  if (/switch|sentry|signal|attention|inspect|review/i.test(hay)) {
    return actions.find((action) => action.kind === 'review_signal') ?? null;
  }
  if (/tunnel|remote ingress|public health/i.test(hay)) {
    return (
      actions.find((action) => action.action_id === 'theater_start_tunnel') ??
      actions.find((action) => action.kind === 'inspect_runtime') ??
      null
    );
  }
  if (/vault|github.*token|probe token|restore runtime/i.test(hay)) {
    return (
      actions.find((action) => action.action_id === 'theater_open_vault') ??
      actions.find((action) => action.kind === 'inspect_runtime') ??
      null
    );
  }
  if (/runtime|command seam|cli/i.test(hay)) {
    return actions.find((action) => action.kind === 'inspect_runtime') ?? null;
  }
  if (/approval|mission control|run\b/i.test(hay)) {
    return (
      actions.find((action) => action.kind === 'approve_run' || action.kind === 'resume_run') ??
      null
    );
  }
  return actions.find((action) => action.kind === 'review_signal') ?? actions[0] ?? null;
}

export function isAutoExecutableCommitment(label: string, action: BriefingAction | null): boolean {
  if (!action) {
    return false;
  }
  if (/^VAXON is attending/i.test(label) || /^I'll attend\b/i.test(label)) {
    return true;
  }
  return /I'll (?:switch|attend|open Attention|open the Lead|clear Approvals|open Mission Control|open the command seam|open Vault|restore runtime|restart the public tunnel)/i.test(
    label,
  );
}

function readinessNeedsRecovery(readiness?: {
  score?: number;
  blockers?: string[];
  grade?: string;
} | null): { recover: boolean; preferVault: boolean; preferTunnel: boolean; blocker: string | null } {
  const score = typeof readiness?.score === 'number' ? readiness.score : 100;
  const blockers = (readiness?.blockers ?? []).map((item) => String(item || '').trim()).filter(Boolean);
  if (score >= 80 && !blockers.length) {
    return { recover: false, preferVault: false, preferTunnel: false, blocker: null };
  }
  const blocker = blockers[0] ?? readiness?.grade ?? null;
  const hay = blockers.join(' ').toLowerCase();
  const preferVault = /vault|cli|auth|key|login|dispatch-ready|runtime not ready/i.test(hay);
  const preferTunnel = /tunnel|remote ingress|public health|edudashpro|network unreachable/i.test(hay);
  return {
    recover: score < 80 || preferVault || preferTunnel,
    preferVault,
    preferTunnel: preferTunnel && !preferVault,
    blocker,
  };
}

function synthesizeRuntimeRecoveryAction(preferVault: boolean): BriefingAction {
  return {
    action_id: preferVault ? 'theater_open_vault' : 'theater_inspect_runtime',
    kind: 'inspect_runtime',
    title: preferVault ? 'Open Vault' : 'Inspect runtime',
    detail: preferVault
      ? 'Unlock Vault so CLI and neural voice can recover.'
      : 'Open the command seam and inspect degraded runtime.',
    workspace_id: null,
    run_id: null,
    signal_id: null,
  };
}

function synthesizeTunnelRepairAction(): BriefingAction {
  return {
    action_id: 'theater_start_tunnel',
    kind: 'inspect_runtime',
    title: 'Restart public tunnel',
    detail: 'Start Cloudflare tunnel and refresh public ingress health.',
    workspace_id: null,
    run_id: null,
    signal_id: null,
  };
}

function promisedWorkspace(
  nextMove: string,
  workspaces: ReportWorkspace[],
): ReportWorkspace | null {
  const hay = nextMove.toLowerCase().replace(/[^a-z0-9]+/g, '');
  return (
    workspaces.find((workspace) => {
      const labels = [
        workspace.display_name,
        workspace.workspace_id.replace(/^workspace[_-]/i, '').replace(/_/g, '-'),
      ];
      return labels.some((label) => {
        const normalized = String(label || '').toLowerCase().replace(/[^a-z0-9]+/g, '');
        return normalized.length > 2 && hay.includes(normalized);
      });
    }) ?? null
  );
}

function synthesizeWorkspaceSwitchAction(
  workspace: ReportWorkspace,
  topSignals: Array<
    Pick<InboxItem, 'signal_id' | 'title' | 'summary' | 'workspace_id'> | null | undefined
  >,
): BriefingAction {
  const signal =
    topSignals.find(
      (row) =>
        row &&
        String(row.workspace_id || '').trim() === workspace.workspace_id &&
        String(row.signal_id || '').trim(),
    ) ?? null;
  const label =
    String(workspace.display_name || '').trim() ||
    workspace.workspace_id.replace(/^workspace[_-]/i, '').replace(/_/g, '-');
  return {
    action_id: `theater_switch_${workspace.workspace_id}`,
    kind: 'review_signal',
    title: String(signal?.title || label).trim() || label,
    detail:
      String(signal?.summary || '').trim() ||
      `Switch to ${label} and open Attention.`,
    workspace_id: workspace.workspace_id,
    run_id: null,
    signal_id: signal ? String(signal.signal_id || '').trim() || null : null,
  };
}

export function buildVaxonReportDirectives(input: {
  nextMove: string;
  actions: BriefingAction[];
  topSignals?: Array<Pick<InboxItem, 'signal_id' | 'title' | 'summary' | 'workspace_id'> | null | undefined>;
  workspaces?: ReportWorkspace[];
  readiness?: {
    score?: number;
    blockers?: string[];
    grade?: string;
  } | null;
}): ReportTheaterDirective[] {
  const recovery = readinessNeedsRecovery(input.readiness);
  const mergedActions = [
    ...input.actions,
    ...synthesizeActionsFromSignals(input.topSignals ?? []).filter(
      (synth) => !input.actions.some((action) => action.signal_id && action.signal_id === synth.signal_id),
    ),
  ];
  const matchedAction = matchActionForNextMove(input.nextMove, mergedActions);
  const promised = promisedWorkspace(input.nextMove, input.workspaces ?? []);
  const wantsTunnel = /tunnel|remote ingress|public health/i.test(input.nextMove);
  let primaryAction =
    matchedAction && promised && matchedAction.kind === 'review_signal'
      ? { ...matchedAction, workspace_id: promised.workspace_id }
      : matchedAction;

  // Spoken next-move named a workspace but briefing actions were empty/stale —
  // still bind a switch so auto-execute and click both work.
  if (!primaryAction && promised && !recovery.recover && !wantsTunnel) {
    primaryAction = synthesizeWorkspaceSwitchAction(promised, input.topSignals ?? []);
  }

  if (wantsTunnel && !recovery.preferVault) {
    primaryAction = synthesizeTunnelRepairAction();
  }

  // Hard gate: do not auto-start investigations while production readiness is blocked.
  if (recovery.recover) {
    if (recovery.preferVault) {
      primaryAction = synthesizeRuntimeRecoveryAction(true);
    } else if (recovery.preferTunnel || wantsTunnel) {
      primaryAction = synthesizeTunnelRepairAction();
    } else {
      primaryAction =
        mergedActions.find((action) => action.kind === 'inspect_runtime') ??
        synthesizeRuntimeRecoveryAction(false);
    }
  }

  const directive = recovery.recover
    ? recovery.preferVault
      ? "I'll open Vault and restore runtime next"
      : recovery.preferTunnel || wantsTunnel
        ? "I'll restart the public tunnel next"
        : "I'll open the command seam and inspect runtime"
    : primaryAction
      ? /switch|review that signal/i.test(input.nextMove)
        ? toVaxonDirectiveLine(input.nextMove)
        : toVaxonActionLabel(primaryAction)
      : toVaxonDirectiveLine(input.nextMove);
  const primaryLabel = directive.replace(/\.$/, '');
  const out: ReportTheaterDirective[] = [
    {
      id: 'vaxon-primary-next',
      label: primaryLabel,
      detail: recovery.recover
        ? recovery.blocker
          ? `Blocked at ${input.readiness?.score ?? '?'}%: ${recovery.blocker}`
          : recovery.preferTunnel || wantsTunnel
            ? 'Restart public ingress before new investigations'
            : 'Restore runtime before new investigations'
        : primaryAction
          ? 'VAXON executes this next'
          : 'Primary directive from this stand-up',
      kind: 'primary',
      briefingAction: primaryAction,
      autoExecute: isAutoExecutableCommitment(primaryLabel, primaryAction),
    },
  ];

  for (const action of mergedActions.slice(0, 3)) {
    if (primaryAction && action.action_id === primaryAction.action_id) {
      continue;
    }
    if (
      primaryAction?.signal_id &&
      action.signal_id &&
      primaryAction.signal_id === action.signal_id
    ) {
      continue;
    }
    const label = toVaxonActionLabel(action);
    if (out.some((item) => item.label.toLowerCase() === label.toLowerCase())) {
      continue;
    }
    out.push({
      id: `vaxon-action:${action.action_id}`,
      label,
      detail:
        action.kind === 'review_signal'
          ? 'Opens Attention on that signal'
          : action.action_id === 'theater_start_tunnel'
            ? 'Restarts Cloudflare public tunnel'
            : action.kind === 'inspect_runtime'
              ? 'Opens the command seam'
              : action.detail?.trim() || action.title,
      kind: 'secondary',
      briefingAction: action,
      autoExecute: false,
    });
  }

  out.push({
    id: 'vaxon-watch',
    label: "I'll keep watching — dismiss for now",
    detail: 'Abort and stay here',
    kind: 'secondary',
    briefingAction: null,
    autoExecute: false,
  });

  return out.slice(0, 4);
}

/**
 * Punchy stage speech — title + at most two concrete lines, no filler monologues.
 * Lead-attributed lines keep the Lead voice: "Mira here. …"
 */
export function stageSpokenLine(title: string, lines: string[]): string {
  const concrete = lines
    .map((line) => line.trim().replace(/\.+$/, ''))
    .filter(Boolean)
    .filter((line) => !isReportTheaterFillerLine(line));
  if (!concrete.length) {
    if (/lead rollups/i.test(title)) {
      return `${title} — Lead standing by.`;
    }
    if (/work in flight/i.test(title)) {
      return `${title} — quiet.`;
    }
    if (/attention/i.test(title)) {
      return `${title} — clear.`;
    }
    return `${title}.`;
  }

  // Lead rollups: speak as the Lead, not as VAXON summarizing.
  if (/lead rollups/i.test(title)) {
    const spoken = concrete.slice(0, 2).map((line) => {
      const match = line.match(/^([^:]+):\s*(.+)$/);
      if (!match) {
        return line;
      }
      const lead = match[1].trim();
      const body = match[2].trim();
      return `${lead} here. ${body}`;
    });
    return spoken.join(' ');
  }

  // Compress “X just completed” lists into one beat.
  if (concrete.every((line) => /just completed$/i.test(line)) && concrete.length > 1) {
    const names = concrete
      .map((line) => line.replace(/\s+just completed$/i, '').trim())
      .filter(Boolean)
      .slice(0, 3);
    return `${title}. ${names.join(', ')} just wrapped.`;
  }
  if (concrete.length === 1 && concrete[0]!.toLowerCase().startsWith(title.toLowerCase())) {
    const line = concrete[0]!;
    return `${line.charAt(0).toUpperCase()}${line.slice(1)}.`;
  }
  const body = concrete.slice(0, 2).join('. ');
  return `${title}. ${body}.`;
}

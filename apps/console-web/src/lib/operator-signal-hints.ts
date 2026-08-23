/** Plain-English alert explainers for a layman operator (VAXON handles the jargon). */

import type { OperatorAlertExplanation as ServerAlertExplanation } from '../contracts/canonical';

export type OperatorAlertExplanation = {
  /** What went wrong, in everyday language. */
  what: string;
  /** What you (the human) should do next. */
  youDo: string;
  /** What an agent should do when handed this issue. */
  agentDo: string;
  /** One short spoken line for VAXON. */
  spoken: string;
};

/** One short spoken line that invites a verbal reply (JARVIS duplex). */
export function askShapedSpoken(body: string, invite: string): string {
  const base = String(body ?? '')
    .trim()
    .replace(/[.!?]+$/, '');
  const ask = String(invite ?? '').trim();
  if (!base) {
    return ask;
  }
  if (!ask) {
    return `${base}.`;
  }
  return `${base}. ${ask}`;
}

function cleanAlertTitle(title: string): string {
  const trimmed = String(title ?? '').trim();
  return trimmed.replace(/^VAXON:\s*/i, '').trim() || trimmed;
}

/** Prefer a concrete Attention ask; never fall back to generic dig-in. */
export function lastResortSpokenInvite(title = ''): string {
  const clean = cleanAlertTitle(title);
  if (clean && clean.length <= 72) {
    return `Open Attention for ${clean}?`;
  }
  return 'Want me to open Attention?';
}

/** Normalize control-plane snake_case explanation into the console view shape. */
export function normalizeServerAlertExplanation(
  raw: ServerAlertExplanation | Record<string, unknown> | null | undefined,
): OperatorAlertExplanation | null {
  if (!raw || typeof raw !== 'object') {
    return null;
  }
  const record = raw as Record<string, unknown>;
  const what = String(record.what ?? '').trim();
  const youDo = String(record.you_do ?? record.youDo ?? '').trim();
  const agentDo = String(record.agent_do ?? record.agentDo ?? '').trim();
  const spoken = String(record.spoken ?? '').trim();
  if (!what || !youDo || !agentDo || !spoken) {
    return null;
  }
  return { what, youDo, agentDo, spoken };
}

/**
 * Prefer control-plane spoken_alert.explanation when it applies to this signal
 * (or to approvals with no signal_id). Fall back to local heuristics.
 */
export function resolveOperatorAlertExplanation(input: {
  signalId?: string;
  title?: string;
  summary?: string | null;
  meta?: Record<string, unknown> | null;
  pendingApprovals?: number;
  reason?: string | null;
  serverExplanation?: ServerAlertExplanation | Record<string, unknown> | null;
  serverSignalId?: string | null;
  serverReason?: string | null;
}): OperatorAlertExplanation {
  const local = explainOperatorAlert({
    signalId: input.signalId,
    title: input.title,
    summary: input.summary,
    meta: input.meta,
    pendingApprovals: input.pendingApprovals,
    reason: input.reason,
  });

  const server = normalizeServerAlertExplanation(input.serverExplanation);
  if (!server) {
    return local;
  }

  const signalId = String(input.signalId ?? '').trim();
  const serverSignalId = String(input.serverSignalId ?? '').trim();
  const serverReason = String(input.serverReason ?? '').trim();
  const pending = Math.max(0, Number(input.pendingApprovals ?? 0) || 0);

  const serverIsApproval =
    serverReason === 'operator_approval_required' ||
    (!serverSignalId && pending > 0);

  if (serverIsApproval && (pending > 0 || input.reason === 'operator_approval_required')) {
    return server;
  }

  if (signalId && serverSignalId && signalId === serverSignalId) {
    return server;
  }

  return local;
}

const BOOTSTRAP_SUMMARY_SIGNAL_IDS = new Set([
  'signal_runtime_summary_degraded',
  'signal_watch_bootstrap_ready',
]);

export function isBootstrapSummarySignal(signalId: string, _title: string): boolean {
  // Match on the exact known placeholder signal IDs only. A loose title
  // substring match (e.g. "bootstrap") would also swallow real errors like
  // "Failed to bootstrap connector after 3 retries" and wrongly tell the
  // operator to ignore them.
  return BOOTSTRAP_SUMMARY_SIGNAL_IDS.has(signalId);
}

function workspaceLabel(meta: Record<string, unknown> | null | undefined): string {
  const fromMeta = String(meta?.workspace_label ?? '').trim();
  if (fromMeta) {
    return fromMeta;
  }
  const workspaceId = String(meta?.workspace_id ?? '').trim();
  if (!workspaceId) {
    return 'this project';
  }
  return workspaceId.replace(/^workspace_/, '').replace(/_/g, ' ');
}

function looksLikeConnectorIssue(title: string, signalId: string): boolean {
  const hay = `${title} ${signalId}`.toLowerCase();
  return (
    /\bconnectors?\b/.test(hay) ||
    /\bunavailable\b/.test(hay) ||
    /\bunreachable\b/.test(hay) ||
    /\boffline\b/.test(hay) ||
    signalId.toLowerCase().includes('connector')
  );
}

function looksLikeAuthOrVault(title: string, summary: string): boolean {
  const hay = `${title} ${summary}`.toLowerCase();
  return (
    /\bvault\b/.test(hay) ||
    /\bcredentials?\b/.test(hay) ||
    /\bapi[_ ]?keys?\b/.test(hay) ||
    /\bunauthorized\b/.test(hay) ||
    /\bauth(entication|orization)?\b/.test(hay) ||
    /\b(access )?tokens?\b/.test(hay)
  );
}

function looksLikeRuntimeUsage(title: string, summary: string): boolean {
  const hay = `${title} ${summary}`.toLowerCase();
  return (
    /\bout of usage\b/.test(hay) ||
    /\busage limit\b/.test(hay) ||
    /\brate limits?\b/.test(hay) ||
    /\bquota\b/.test(hay) ||
    /\bactionrequired\b/.test(hay)
  );
}

function looksLikeDegraded(title: string, summary: string, signalId: string): boolean {
  const hay = `${title} ${summary} ${signalId}`.toLowerCase();
  return /\bdegraded\b/.test(hay) || /\bstale\b/.test(hay) || /\bunhealthy\b/.test(hay);
}

function metaPlainOverride(
  meta: Record<string, unknown> | null,
): Partial<OperatorAlertExplanation> | null {
  if (!meta) {
    return null;
  }
  const what = String(meta.operator_what ?? meta.plain_english ?? '').trim();
  const youDo = String(meta.operator_you_do ?? meta.recommended_detail ?? '').trim();
  const agentDo = String(meta.operator_agent_do ?? '').trim();
  const spoken = String(meta.operator_spoken ?? '').trim();
  if (!what && !youDo && !agentDo) {
    return null;
  }
  return {
    ...(what ? { what } : {}),
    ...(youDo ? { youDo } : {}),
    ...(agentDo ? { agentDo } : {}),
    ...(spoken ? { spoken } : {}),
  };
}

/**
 * Translate a technical signal into layman copy + agent instructions.
 * VAXON is the technical partner; the operator gets plain English.
 */
export function explainOperatorAlert(input: {
  signalId?: string;
  title?: string;
  summary?: string | null;
  severity?: string | null;
  meta?: Record<string, unknown> | null;
  pendingApprovals?: number;
  reason?: string | null;
}): OperatorAlertExplanation {
  const signalId = String(input.signalId ?? '').trim();
  const title = String(input.title ?? '').trim() || 'Attention item';
  const summary = String(input.summary ?? '').trim();
  const meta = input.meta ?? null;
  const family = String(meta?.signal_family ?? '').trim();
  const pending = Math.max(0, Number(input.pendingApprovals ?? 0) || 0);
  const reason = String(input.reason ?? '').trim();

  if (reason === 'operator_approval_required' || pending > 0) {
    const count = pending > 0 ? pending : 1;
    const noun = count === 1 ? 'one agent job' : `${count} agent jobs`;
    return {
      what: `${noun} ${count === 1 ? 'is' : 'are'} paused and waiting for your go-ahead.`,
      youDo: 'Open Approvals, read the short summary, then tap Approve (let it continue) or Reject (stop it).',
      agentDo:
        'Do not continue until the operator approves. After approval, resume the paused run and finish the original task. After reject, stop cleanly and leave a short note of what was cancelled.',
      spoken: askShapedSpoken(
        count === 1
          ? 'One job is waiting for your yes or no before I continue'
          : `${count} jobs are waiting for your yes or no before I continue`,
        'Approve or reject?',
      ),
    };
  }

  if (family === 'email_triage') {
    const sender = String(meta?.sender ?? 'someone').trim() || 'someone';
    const action = String(meta?.recommended_action ?? 'follow up').replace(/_/g, ' ');
    return {
      what: `An email from ${sender} needs a human decision (${action}).`,
      youDo: 'Open Attention, skim the email thread, then hand it to the agent if you want a draft reply or investigation.',
      agentDo: `Triage the email from ${sender}. Draft a reply or investigate the request, then pause for the operator to send or approve.`,
      spoken: askShapedSpoken(`Email from ${sender} needs a quick look`, 'Shall I triage it?'),
    };
  }

  if (family === 'child_project_monitor') {
    const label = workspaceLabel(meta);
    const status = String(meta?.monitor_status ?? 'a warning').trim() || 'a warning';
    return {
      what: `${label} raised ${status} on an outside service it watches (for example errors or downtime).`,
      youDo: 'Open the project’s Attention details. If it mentions missing keys, unlock Vault and add the credentials. Otherwise hand it to the agent.',
      agentDo: `Investigate the ${label} monitor alert (${status}). Check the linked service dashboard, confirm whether it is a real outage or a config gap, fix what is safe, and report back in plain English.`,
      spoken: askShapedSpoken(
        `${label} needs attention — something outside the app looked unhealthy`,
        `Open Attention for ${label}?`,
      ),
    };
  }

  const override = metaPlainOverride(meta);
  if (override?.what && override.youDo && override.agentDo) {
    return {
      what: override.what,
      youDo: override.youDo,
      agentDo: override.agentDo,
      spoken:
        override.spoken ||
        askShapedSpoken(`Heads up — ${cleanAlertTitle(title)}`, lastResortSpokenInvite(title)),
    };
  }

  if (signalId.startsWith('signal_connector_') || looksLikeConnectorIssue(title, signalId)) {
    const project = workspaceLabel(meta);
    return {
      what: `A connection Axon needs for ${project} is down or not answering.`,
      youDo: 'Check that the related service is running, then ask the agent to re-check. If it keeps failing, open Vault for missing credentials.',
      agentDo: `Diagnose why the connector for "${title}" is unavailable. Verify the service is up, credentials are valid, and restore the link. Explain the fix in plain English.`,
      spoken: askShapedSpoken(
        'A connection Axon needs is down — I can help get it back',
        'Shall I diagnose it?',
      ),
    };
  }

  if (isBootstrapSummarySignal(signalId, title)) {
    return {
      what: 'This is a normal “still warming up” note while Watch finishes connecting — not an outage.',
      youDo: 'You can ignore it, or keep using Command as usual. No repair step is required.',
      agentDo: 'Do not treat this as an incident. Confirm Watch is connected, then continue with the operator’s real request.',
      spoken: askShapedSpoken(
        'Just a warm-up note — nothing broken on your side',
        'Want me to confirm Watch?',
      ),
    };
  }

  if (looksLikeRuntimeUsage(title, summary)) {
    return {
      what: 'The coding agent could not start because its usage limit or login is blocked.',
      youDo: 'Open Runtime / Vault, switch model or top up Cursor usage, then retry the job.',
      agentDo: 'Do not retry blindly. Tell the operator which runtime is blocked and the exact fix (usage, login, or model switch), then wait for them.',
      spoken: askShapedSpoken(
        'The agent could not start — usage or login needs a quick fix first',
        'Shall I walk you through it?',
      ),
    };
  }

  if (looksLikeAuthOrVault(title, summary)) {
    return {
      what: 'A locked vault or missing key is stopping a connected service from working.',
      youDo: 'Open Vault, unlock it, and make sure the needed key is present. Then retry.',
      agentDo: 'Identify which key or unlock step is missing. Guide the operator to Vault; do not invent secrets. After unlock, re-check the failing connection.',
      spoken: askShapedSpoken(
        'A key or vault unlock is needed before this can continue',
        'Shall I guide you to Vault?',
      ),
    };
  }

  if (looksLikeDegraded(title, summary, signalId)) {
    return {
      what: 'Part of the system is running in a weaker “degraded” mode — some status may be incomplete.',
      youDo: 'Glance at the status strip. If something you need looks wrong, hand it to the agent; otherwise you can keep working.',
      agentDo: `Explain the degraded condition for "${title}" in plain English, list what still works, and fix or restart the unhealthy piece if it is safe.`,
      spoken: askShapedSpoken(
        'Something is running in a weaker mode — worth a quick look, not a panic',
        'Want me to check it?',
      ),
    };
  }

  // Generic uncommon-signal fallback — structured, no keyword guessing.
  const detail = summary && summary.toLowerCase() !== title.toLowerCase() ? summary : title;
  const severity = String(input.severity ?? meta?.severity ?? '').trim().toLowerCase();
  const severityHint =
    severity === 'critical' || severity === 'high'
      ? 'This looks urgent.'
      : 'This may be informational.';
  const what = override?.what || `Axon flagged something that needs a look: ${detail}`;
  const youDo =
    override?.youDo ||
    `Open Attention Details for the plain-English guide. ${severityHint} Then Approve, hand off to the agent, or Clear if it is noise.`;
  const agentDo =
    override?.agentDo ||
    `Investigate "${title}". Do not assume a category — read the signal summary and meta, summarize in plain English for a non-technical operator, fix only what is safe, and say exactly what changed.`;
  return {
    what,
    youDo,
    agentDo,
    spoken:
      override?.spoken ||
      askShapedSpoken(`Heads up — ${cleanAlertTitle(title)}`, lastResortSpokenInvite(title)),
  };
}

/** Flattened hint used by existing call sites that expect a single paragraph. */
export function signalOperatorHint(input: {
  signalId: string;
  title: string;
  summary?: string | null;
  meta?: Record<string, unknown> | null;
}): string {
  const explained = explainOperatorAlert({
    signalId: input.signalId,
    title: input.title,
    summary: input.summary,
    meta: input.meta,
  });
  return `What happened: ${explained.what} What you should do: ${explained.youDo} What the agent should do: ${explained.agentDo}`;
}

export function watchRuleLabel(mode: string | undefined): string {
  switch ((mode ?? 'observe').toLowerCase()) {
    case 'observe':
      return 'Watching';
    case 'advise':
      return 'Advice';
    case 'approval':
      return 'Needs you';
    case 'execute':
      return 'Acting';
    default:
      return mode ?? 'Watching';
  }
}

export function watchRuleTooltip(mode: string | undefined): string {
  switch ((mode ?? 'observe').toLowerCase()) {
    case 'observe':
      return 'VAXON is only watching — no action needed from you.';
    case 'advise':
      return 'VAXON has advice. You decide whether to act or ask the agent.';
    case 'approval':
      return 'VAXON is waiting for your Approve or Reject.';
    case 'execute':
      return 'VAXON may interrupt — review before ignoring.';
    default:
      return 'Status only — not a button.';
  }
}

export function deliveryStateLabel(state: string | undefined): string {
  if (!state || state === 'not_required') {
    return '';
  }
  if (state === 'delivered') {
    return 'Sent';
  }
  if (state === 'pending') {
    return 'Sending';
  }
  return state.charAt(0).toUpperCase() + state.slice(1);
}

export function deliveryStateTooltip(state: string | undefined): string {
  if (state === 'delivered') {
    return 'This alert was already delivered (status only).';
  }
  if (state === 'pending') {
    return 'Delivery still in progress (status only).';
  }
  return 'Delivery status only — not a button.';
}

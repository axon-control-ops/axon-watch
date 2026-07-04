import type { OperatorBriefing, RunRecord, RuntimeSummary, WorkspaceRecord } from '../contracts/canonical';
import type { KairoPresenceState } from './kairo-presence';
import type { RuntimeSummaryLoadState } from './runtime-strip';

export interface TopbarMetaPill {
  id: string;
  label: string;
  tone: 'default' | 'brand' | 'success';
}

export interface TopbarRuntimeVersionChip {
  id: string;
  label: string;
  version: string;
  icon: 'code' | 'policy' | 'axon';
}

export function buildMockupTopbarBreadcrumb(): string {
  return 'Axon-X Bootstrap / bootstrap-model';
}

export function buildTopbarRuntimeVersionChips(
  _runtimeSummary: RuntimeSummary | null,
): TopbarRuntimeVersionChip[] {
  return [
    { id: 'kairo-code', label: 'KAIRO.CODE', version: 'v1.4.2', icon: 'code' },
    { id: 'policy', label: 'POLICY', version: 'v2.1.0', icon: 'policy' },
    { id: 'axon-x', label: 'AXON-X', version: 'v0.9.8', icon: 'axon' },
  ];
}

export interface StatusBarZoneItem {
  id: string;
  label: string;
  tone?: 'default' | 'success' | 'warning' | 'brand';
}

export interface StatusBarZones {
  left: StatusBarZoneItem[];
  center: StatusBarZoneItem[];
  right: StatusBarZoneItem[];
}

export function buildTopbarMetaPills(runtimeSummary: RuntimeSummary | null): TopbarMetaPill[] {
  if (!runtimeSummary) {
    return [{ id: 'runtime', label: 'RUNTIME', tone: 'default' }];
  }

  const pills: TopbarMetaPill[] = [
    {
      id: 'runtime',
      label: runtimeSummary.control_plane.ready ? 'RUNTIME READY' : 'RUNTIME',
      tone: runtimeSummary.control_plane.ready ? 'success' : 'default',
    },
    {
      id: 'control-plane',
      label: `CP v${runtimeSummary.control_plane.version}`,
      tone: 'brand',
    },
    {
      id: 'model',
      label: runtimeSummary.runtime_identity.model_name.toUpperCase(),
      tone: 'brand',
    },
  ];

  if (runtimeSummary.watch.connected) {
    pills.push({ id: 'watch', label: 'WATCH ONLINE', tone: 'success' });
  } else {
    pills.push({ id: 'watch', label: 'WATCH OFFLINE', tone: 'default' });
  }

  return pills;
}

export function buildTopbarBreadcrumb(
  runtimeSummary: RuntimeSummary | null,
  workspace: WorkspaceRecord | null,
): string {
  const workspaceLabel = workspace?.workspace_id ?? 'no workspace';
  const provider = runtimeSummary?.runtime_identity.provider_name ?? 'Axon-X Bootstrap';
  const model = runtimeSummary?.runtime_identity.model_name ?? 'bootstrap-model';
  return `${workspaceLabel} / ${provider} / ${model}`;
}

export function kairoPresenceModuleLabel(state: KairoPresenceState): string {
  const parts = kairoPresenceModuleParts(state);
  return `${parts.title} ${parts.subtitle}`;
}

export function kairoPresenceModuleParts(state: KairoPresenceState): {
  title: string;
  subtitle: string;
} {
  switch (state) {
    case 'listening':
      return { title: 'KAIRO', subtitle: 'LISTENING' };
    case 'speaking':
      return { title: 'KAIRO', subtitle: 'SPEAKING' };
    case 'alerting':
      return { title: 'KAIRO', subtitle: 'ATTENTION' };
    case 'observing':
      return { title: 'KAIRO', subtitle: 'LISTENING' };
    case 'privacy_blocked':
      return { title: 'KAIRO', subtitle: 'MUTED' };
    default:
      return { title: 'KAIRO', subtitle: 'STANDBY' };
  }
}

export function buildBriefingSummaryLine(
  briefing: OperatorBriefing | null,
  runtimeSummary: RuntimeSummary | null,
  workspaceId: string | null,
): string {
  const activeRunSource = briefing?.active_runs ?? runtimeSummary?.active_runs ?? [];
  const activeRuns = workspaceId
    ? activeRunSource.filter((run) => run.workspace_id === workspaceId).length
    : activeRunSource.length;
  const signalCount =
    briefing?.top_signals.length ?? runtimeSummary?.signals.open_count ?? 0;
  const approvals = briefing?.pending_approvals.count ?? runtimeSummary?.approvals.pending_count ?? 0;

  if (approvals > 0) {
    return `${activeRuns} active run${activeRuns === 1 ? '' : 's'} • ${approvals} approval${approvals === 1 ? '' : 's'} require review`;
  }

  if (signalCount > 0) {
    return `${activeRuns} active run${activeRuns === 1 ? '' : 's'} • ${signalCount} signal${signalCount === 1 ? '' : 's'} require review`;
  }

  return `${activeRuns} active run${activeRuns === 1 ? '' : 's'} • systems nominal`;
}

export function buildBriefingHeroSubtitle(
  briefing: OperatorBriefing | null,
  loadState: 'idle' | 'loading' | 'loaded' | 'error',
): string {
  if (loadState === 'loading' && !briefing) {
    return 'Standing by while briefing loads.';
  }

  if (loadState === 'error' && !briefing) {
    return 'Briefing unavailable. Check control-plane connectivity.';
  }

  if (briefing?.pending_approvals.count) {
    return 'Approvals need your review before I can continue.';
  }

  if (briefing?.top_signals.length) {
    return 'Top signals need review. Tell me what to focus on.';
  }

  if (briefing?.degraded.active) {
    return 'Runtime is degraded. Review the status strip before continuing.';
  }

  return "I'm listening. Tell me what to focus on.";
}

export function runPhaseProgress(phase: RunRecord['phase'] | null | undefined): number {
  switch (phase) {
    case 'planning':
      return 18;
    case 'executing':
      return 68;
    case 'awaiting_approval':
      return 52;
    case 'review_ready':
      return 84;
    case 'completed':
      return 100;
    default:
      return 32;
  }
}

export function runPhaseTag(phase: RunRecord['phase'] | 'idle' | null | undefined): string {
  if (!phase || phase === 'idle') {
    return 'IDLE';
  }
  if (phase === 'executing') {
    return 'EXECUTE';
  }
  return phase.replace(/_/g, ' ').toUpperCase();
}

export const MOCKUP_WORKSPACE_IDS = [
  'workspace_smoke',
  'workspace_recsys',
  'workspace_finance',
  'workspace_nlp',
  'workspace_cv',
  'workspace_edge',
  'workspace_research',
] as const;

export type MockupWorkspaceId = (typeof MOCKUP_WORKSPACE_IDS)[number];

export const DEFAULT_OPERATOR_WORKSPACE_ID: MockupWorkspaceId = MOCKUP_WORKSPACE_IDS[0];

export function isOperatorWorkspaceId(workspaceId: string | null | undefined): boolean {
  if (!workspaceId) {
    return false;
  }

  return MOCKUP_WORKSPACE_IDS.includes(workspaceId as MockupWorkspaceId);
}

export function mergeMockupWorkspaceCatalog(items: WorkspaceRecord[]): WorkspaceRecord[] {
  const byId = new Map(items.map((item) => [item.workspace_id, item]));
  return MOCKUP_WORKSPACE_IDS.map((workspaceId) => {
    return byId.get(workspaceId) ?? { workspace_id: workspaceId };
  });
}

export function resolveBootstrapWorkspaceId(
  workspaces: WorkspaceRecord[],
  primaryRun: RunRecord | null,
): string | null {
  if (workspaces.length === 0) {
    return null;
  }

  const runWorkspaceId = primaryRun?.workspace_id ?? null;
  if (runWorkspaceId && isOperatorWorkspaceId(runWorkspaceId)) {
    const runWorkspace = workspaces.find((workspace) => workspace.workspace_id === runWorkspaceId);
    if (runWorkspace) {
      return runWorkspace.workspace_id;
    }
  }

  const defaultWorkspace = workspaces.find(
    (workspace) => workspace.workspace_id === DEFAULT_OPERATOR_WORKSPACE_ID,
  );
  if (defaultWorkspace) {
    return defaultWorkspace.workspace_id;
  }

  return workspaces[0]?.workspace_id ?? DEFAULT_OPERATOR_WORKSPACE_ID;
}

export function workspaceRunCount(
  workspaceId: string,
  countsByWorkspace: Record<string, number> = {},
): number {
  return countsByWorkspace[workspaceId] ?? 0;
}

export function workspaceStatusLine(
  workspaceId: string,
  isActive: boolean,
  countsByWorkspace: Record<string, number> = {},
): string {
  const count = workspaceRunCount(workspaceId, countsByWorkspace);
  const runLabel = `${count} run${count === 1 ? '' : 's'}`;
  return isActive ? `Active • ${runLabel}` : `Idle • ${runLabel}`;
}

function formatSummaryAge(isoTimestamp: string): string {
  const generatedAt = Date.parse(isoTimestamp);
  if (Number.isNaN(generatedAt)) {
    return 'unknown';
  }

  const elapsedSeconds = Math.max(0, Math.floor((Date.now() - generatedAt) / 1000));
  if (elapsedSeconds < 60) {
    return `${elapsedSeconds}s ago`;
  }

  const elapsedMinutes = Math.floor(elapsedSeconds / 60);
  if (elapsedMinutes < 60) {
    return `${elapsedMinutes}m ago`;
  }

  const elapsedHours = Math.floor(elapsedMinutes / 60);
  return `${elapsedHours}h ago`;
}

export interface WorkspaceStatusCardRow {
  label: string;
  value: string;
}

export function buildWorkspaceStatusCardRows(input: {
  runtimeSummary: RuntimeSummary | null;
  runtimeSummaryLoadState: RuntimeSummaryLoadState;
}): WorkspaceStatusCardRow[] {
  if (input.runtimeSummaryLoadState === 'loading') {
    return [
      { label: 'Environment', value: 'loading…' },
      { label: 'Last Summary', value: 'loading…' },
      { label: 'Control Plane', value: 'loading…' },
      { label: 'Signals', value: '…' },
    ];
  }

  if (input.runtimeSummaryLoadState === 'error' || !input.runtimeSummary) {
    return [
      { label: 'Environment', value: 'unavailable' },
      { label: 'Last Summary', value: 'unavailable' },
      { label: 'Control Plane', value: 'unavailable' },
      { label: 'Signals', value: '0' },
    ];
  }

  const summary = input.runtimeSummary;
  return [
    { label: 'Environment', value: 'dev-west-1' },
    { label: 'Last Activity', value: formatSummaryAge(summary.generated_at) },
    { label: 'Storage', value: '42.7 GB' },
    { label: 'Signals', value: String(summary.signals.open_count) },
  ];
}

export function buildStatusBarZones(input: {
  runtimeSummary: RuntimeSummary | null;
  runtimeSummaryLoadState: RuntimeSummaryLoadState;
  primaryActiveRun: RunRecord | null;
  workspaceId: string | null;
}): StatusBarZones {
  if (input.runtimeSummaryLoadState === 'loading') {
    return {
      left: [{ id: 'loading', label: 'LOADING RUNTIME…', tone: 'default' }],
      center: [],
      right: [],
    };
  }

  if (input.runtimeSummaryLoadState === 'error' || !input.runtimeSummary) {
    return {
      left: [{ id: 'unavailable', label: 'RUNTIME UNAVAILABLE', tone: 'warning' }],
      center: [],
      right: [],
    };
  }

  const summary = input.runtimeSummary;
  const watchConnected = summary.watch.connected;
  const watchStatus = summary.watch.status.toUpperCase();
  const openSignals = summary.signals.open_count;
  const phase = input.primaryActiveRun?.phase ?? 'idle';
  const workspaceLabel = input.workspaceId ?? 'no workspace';

  return {
    left: [
      {
        id: 'watch',
        label: watchConnected ? 'WATCH CONNECTED' : 'WATCH OFFLINE',
        tone: watchConnected ? 'success' : 'warning',
      },
      { id: 'agent', label: `WATCH ${watchStatus}`, tone: 'default' },
      { id: 'version', label: `v${summary.control_plane.version}`, tone: 'default' },
    ],
    center: [
      { id: 'phase', label: `RUN PHASE: ${runPhaseTag(phase)}`, tone: 'brand' },
      {
        id: 'signals',
        label: `SIGNALS: ${openSignals} ACTIVE`,
        tone: openSignals > 0 ? 'warning' : 'default',
      },
    ],
    right: [{ id: 'workspace', label: `WORKSPACE: ${workspaceLabel}`, tone: 'default' }],
  };
}

export function workspaceIconKind(workspaceId: string): string {
  if (workspaceId.includes('smoke')) {
    return 'cube';
  }
  if (workspaceId.includes('recsys')) {
    return 'cube';
  }
  if (workspaceId.includes('finance')) {
    return 'building';
  }
  if (workspaceId.includes('nlp')) {
    return 'chat';
  }
  if (workspaceId.includes('cv')) {
    return 'lens';
  }
  if (workspaceId.includes('edge')) {
    return 'tower';
  }
  if (workspaceId.includes('research')) {
    return 'flask';
  }
  if (workspaceId.includes('bootstrap')) {
    return 'orbit';
  }
  if (workspaceId.includes('alpha')) {
    return 'hex';
  }
  return 'hex';
}

/** @deprecated Use workspaceIconKind + CSS glyphs */
export function workspaceIcon(workspaceId: string): string {
  if (workspaceId.includes('smoke')) {
    return '⧉';
  }
  if (workspaceId.includes('recsys')) {
    return '▣';
  }
  if (workspaceId.includes('finance')) {
    return '⛫';
  }
  if (workspaceId.includes('nlp')) {
    return '◎';
  }
  if (workspaceId.includes('cv')) {
    return '◉';
  }
  if (workspaceId.includes('edge')) {
    return '△';
  }
  if (workspaceId.includes('research')) {
    return '⚗';
  }
  if (workspaceId.includes('bootstrap')) {
    return '◎';
  }
  if (workspaceId.includes('alpha')) {
    return '⬡';
  }
  return '⬡';
}

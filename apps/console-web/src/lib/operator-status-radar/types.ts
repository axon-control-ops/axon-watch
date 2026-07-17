export type OperatorRadarTone = 'nominal' | 'watch' | 'attention' | 'degraded';
export type OperatorStatusMetricTone = 'default' | 'ok' | 'warn' | 'attention';

export interface OperatorStatusMetric {
  label: string;
  value: string;
  tone: OperatorStatusMetricTone;
}

export interface OperatorMissionSummary {
  runId: string;
  displayName: string;
  shortId: string;
  identityLabel: string;
  phase: string;
  workspace: string;
  status: string;
  elapsed: string;
  currentStep: string;
  watchConnected: boolean;
}

export interface OperatorMissionStep {
  label: string;
  tone: 'done' | 'active' | 'pending';
  meta?: string;
}

export interface OperatorMissionCard {
  label: string;
  value: string;
  tone: OperatorStatusMetricTone;
}

export interface OperatorMissionChip {
  label: string;
  value: string;
  tone: OperatorStatusMetricTone;
}

export interface OperatorExecutionStage {
  runId: string;
  displayName: string;
  shortId: string;
  identityLabel: string;
  phase: string;
  phaseProgress: number;
  summary: string;
  commandDetail: string | null;
  currentStep: string;
  notice: string;
  advise: string;
  decide: string;
  elapsed: string;
  hasActiveRun: boolean;
}

export interface OperatorLiveFeedItem {
  id: string;
  label: string;
  meta?: string;
  tone: 'done' | 'active' | 'info' | 'pending';
}

export interface OperatorAgentSummaryItem {
  id: string;
  label: string;
  meta?: string;
}

export type OperatorStatusRailAction = 'focus-connectors';

export interface OperatorStatusRailItem {
  label: string;
  value: string;
  tone: OperatorStatusMetricTone;
  action?: OperatorStatusRailAction;
}

export type OperatorStatusLoadState = 'idle' | 'loading' | 'loaded' | 'error';

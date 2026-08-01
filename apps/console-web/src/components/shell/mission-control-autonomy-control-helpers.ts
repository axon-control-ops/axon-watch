export type AutonomyWorkerStatusLike = {
  blocked_by_env?: boolean;
  effective_enabled?: boolean;
} | null;

export type AutonomyScanLike = {
  created_count?: number;
  escalated_count?: number;
} | null;

export type AutonomyReadinessLike = {
  grade?: string;
  score?: number;
} | null;

export function resolveAutonomyWorkerStateLabel(input: {
  status: AutonomyWorkerStatusLike;
  autonomousOn: boolean;
}): string {
  const { status, autonomousOn } = input;
  if (!status) {
    return 'Unknown';
  }
  if (status.blocked_by_env) {
    return 'Blocked';
  }
  if (autonomousOn && status.effective_enabled) {
    return 'Running';
  }
  if (autonomousOn) {
    return 'Armed';
  }
  return 'Paused';
}

export function buildAutonomyTelemetryLine(input: {
  workerStateLabel: string;
  autonomyMode: string;
  scan: AutonomyScanLike;
  readiness: AutonomyReadinessLike;
}): string {
  const parts = [input.workerStateLabel, input.autonomyMode];
  const scan = input.scan;
  if (scan) {
    parts.push(`+${scan.created_count ?? 0}`);
    if ((scan.escalated_count ?? 0) > 0) {
      parts.push(`↑${scan.escalated_count}`);
    }
  }
  if (input.readiness && input.readiness.grade !== 'ready') {
    parts.push(`${input.readiness.score}/100`);
  }
  return parts.join(' · ');
}

export function shouldShowAutonomyAlert(input: {
  actionMessage: string | null | undefined;
  feedError: string | null | undefined;
  blockedByEnv: boolean;
  readiness: AutonomyReadinessLike;
}): boolean {
  return (
    Boolean(input.actionMessage) ||
    Boolean(input.feedError) ||
    input.blockedByEnv ||
    Boolean(input.readiness && input.readiness.grade !== 'ready')
  );
}

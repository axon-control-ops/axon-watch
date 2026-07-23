import type { GalaxyPresencePhase } from '../brain-galaxy/galaxy-presence-state';

export type MotionIntensity = 'off' | 'subtle' | 'cinematic';

export type MotionTransitionKind =
  | 'node_select'
  | 'panel_open'
  | 'panel_close'
  | 'artifact_open'
  | 'run_packet'
  | 'alert_sweep'
  | 'presence';

export type MotionPlan = {
  kind: MotionTransitionKind;
  durationMs: number;
  easing: string;
  cameraDolly: boolean;
  settleOnly: boolean;
};

const INTENSITY_SCALE: Record<MotionIntensity, number> = {
  off: 0,
  subtle: 0.55,
  cinematic: 1,
};

export type MotionPlanOptions = {
  intensity?: MotionIntensity;
  reducedMotion?: boolean;
  presencePhase?: GalaxyPresencePhase | null;
};

/**
 * Single motion orchestrator — maps presence/transition intent to a plan.
 * Components must not invent independent pulse loops.
 */
export function planMotionTransition(
  kind: MotionTransitionKind,
  options: MotionPlanOptions = {},
): MotionPlan {
  const intensity = options.intensity ?? 'subtle';
  const reducedMotion = options.reducedMotion ?? false;
  const presencePhase = options.presencePhase ?? null;
  const scale = reducedMotion || intensity === 'off' ? 0 : INTENSITY_SCALE[intensity];
  const base = BASE_PLANS[kind];
  const durationMs = Math.round(base.durationMs * scale);
  return {
    ...base,
    durationMs,
    cameraDolly: scale > 0 && base.cameraDolly,
    settleOnly: kind === 'alert_sweep' || presencePhase === 'alerting',
  };
}

const BASE_PLANS: Record<MotionTransitionKind, MotionPlan> = {
  node_select: {
    kind: 'node_select',
    durationMs: 420,
    easing: 'var(--motion-spring)',
    cameraDolly: true,
    settleOnly: false,
  },
  panel_open: {
    kind: 'panel_open',
    durationMs: 280,
    easing: 'var(--motion-ease-out)',
    cameraDolly: false,
    settleOnly: false,
  },
  panel_close: {
    kind: 'panel_close',
    durationMs: 220,
    easing: 'var(--motion-ease-in)',
    cameraDolly: false,
    settleOnly: false,
  },
  artifact_open: {
    kind: 'artifact_open',
    durationMs: 360,
    easing: 'var(--motion-ease-out)',
    cameraDolly: false,
    settleOnly: false,
  },
  run_packet: {
    kind: 'run_packet',
    durationMs: 520,
    easing: 'linear',
    cameraDolly: false,
    settleOnly: false,
  },
  alert_sweep: {
    kind: 'alert_sweep',
    durationMs: 480,
    easing: 'var(--motion-ease-out)',
    cameraDolly: false,
    settleOnly: true,
  },
  presence: {
    kind: 'presence',
    durationMs: 300,
    easing: 'var(--motion-spring)',
    cameraDolly: false,
    settleOnly: false,
  },
};

export function motionIntensityFromStorage(
  raw: string | null | undefined,
): MotionIntensity {
  if (raw === 'off' || raw === 'cinematic' || raw === 'subtle') {
    return raw;
  }
  return 'subtle';
}

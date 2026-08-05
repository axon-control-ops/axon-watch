function controlPlaneBaseUrl(): string {
  const configured = import.meta.env.VITE_CONTROL_PLANE_BASE_URL;
  return typeof configured === 'string' ? configured.replace(/\/$/, '') : '';
}

export type KairoConverseTurnKind =
  | 'status_question'
  | 'open_question'
  | 'command'
  | 'chat'
  | 'action';
export type KairoConverseSource = 'template' | 'model' | 'fallback';
export type KairoConverseAnswerTier = 'fast' | 'deep';
export type KairoConverseSubmissionIntent = 'ask' | 'dispatch';

export type KairoConverseAction =
  | {
      type: 'handoff_signal';
      signal_id: string;
      target_workspace_id: string;
      task: string;
      employee_id?: string | null;
      employee_role?: string | null;
      employee_name?: string | null;
      routing_receipt?: string | null;
      model_receipt?: Record<string, unknown> | null;
    }
  | {
      type: 'route_employee';
      target_workspace_id: string;
      task: string;
      employee_id: string;
      employee_role: string;
      employee_name: string;
      routing_receipt?: string | null;
      model_receipt?: Record<string, unknown> | null;
    }
  | {
      type: 'lead_fan_out';
      target_workspace_id: string;
      task: string;
      mode?: string | null;
      tasks?: unknown[];
      runs?: unknown[];
      deferred?: unknown[];
      receipt?: unknown;
      plan?: unknown;
    }
  | {
      type: 'dispatch_command';
      content: string;
    }
  | {
      type: 'focus_briefing';
    }
  | {
      type: 'move_voice_orb';
      dock?: 'top-left' | 'top-right' | 'bottom-left' | 'bottom-right' | 'center';
      mode?: 'smart_dodge';
    }
  | {
      type: 'switch_workspace';
      workspace_id: string;
      open_file_path?: string | null;
    }
  | {
      type: 'start_tunnel';
      outcome?: string;
      tunnel?: Record<string, unknown> | null;
    }
  | {
      type: 'clear_stale_ci_alerts';
      resolved_count?: number;
      resolved_signal_ids?: string[];
    };

export interface KairoConverseArtifactAction {
  label: string;
  ui_action: Record<string, unknown> | null;
}

export interface KairoConverseArtifactSource {
  label: string;
  detail: string;
}

export interface KairoConverseArtifact {
  artifact_id: string;
  title: string;
  summary: string;
  body: string;
  sources: KairoConverseArtifactSource[];
  actions: KairoConverseArtifactAction[];
}

export interface KairoConverseRequest {
  content: string;
  session_id?: string;
  workspace_id?: string;
  use_runtime?: boolean;
  answer_tier?: KairoConverseAnswerTier;
  context_workspace_id?: string;
  context_signal_id?: string;
  context_node_id?: string;
  attachment_ids?: string[];
  /** Server-enforced permission boundary; omitted clients are Ask-only. */
  submission_intent?: KairoConverseSubmissionIntent;
}

export interface KairoConverseReportSections {
  attention: string[];
  work_in_flight: string[];
  lead_rollups: string[];
  fleet: string[];
  next_move: string;
}

export interface KairoConverseReport {
  sections: KairoConverseReportSections;
  fingerprint?: string | null;
  lane?: string | null;
}

export interface KairoConverseResponse {
  turn_kind: KairoConverseTurnKind;
  reply: string;
  /** Optional shorter line for TTS; UI should prefer `reply`. */
  spoken_reply?: string | null;
  source: KairoConverseSource;
  command_content: string | null;
  requires_confirmation?: boolean | null;
  action_tier?: string | null;
  dispatch_lane?: string | null;
  voice_routing_mode?: string | null;
  routing_receipt?: string | null;
  model_receipt?: Record<string, unknown> | null;
  action: KairoConverseAction | null;
  artifacts: KairoConverseArtifact[];
  /** Structured stand-up payload for command-theater overlay. */
  report?: KairoConverseReport | null;
  submission_intent?: KairoConverseSubmissionIntent;
}

export async function postKairoConverse(body: KairoConverseRequest): Promise<KairoConverseResponse> {
  const baseUrl = controlPlaneBaseUrl();
  const url = baseUrl ? `${baseUrl}/api/kairo/converse` : '/api/kairo/converse';
  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    throw new Error(`KAIRO converse failed (${response.status})`);
  }
  return (await response.json()) as KairoConverseResponse;
}

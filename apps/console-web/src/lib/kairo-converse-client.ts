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

export type KairoConverseAction =
  | {
      type: 'handoff_signal';
      signal_id: string;
      target_workspace_id: string;
      task: string;
    }
  | {
      type: 'dispatch_command';
      content: string;
    }
  | {
      type: 'focus_briefing';
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
}

export interface KairoConverseResponse {
  turn_kind: KairoConverseTurnKind;
  reply: string;
  source: KairoConverseSource;
  command_content: string | null;
  requires_confirmation?: boolean | null;
  action: KairoConverseAction | null;
  artifacts: KairoConverseArtifact[];
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

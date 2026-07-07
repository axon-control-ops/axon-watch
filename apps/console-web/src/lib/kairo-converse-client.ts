function controlPlaneBaseUrl(): string {
  const configured = import.meta.env.VITE_CONTROL_PLANE_BASE_URL;
  return typeof configured === 'string' ? configured.replace(/\/$/, '') : '';
}

export type KairoConverseTurnKind = 'status_question' | 'open_question' | 'command' | 'chat';
export type KairoConverseSource = 'template' | 'model' | 'fallback';

export interface KairoConverseRequest {
  content: string;
  session_id?: string;
  workspace_id?: string;
  use_runtime?: boolean;
}

export interface KairoConverseResponse {
  turn_kind: KairoConverseTurnKind;
  reply: string;
  source: KairoConverseSource;
  command_content: string | null;
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

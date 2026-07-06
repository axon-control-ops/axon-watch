function controlPlaneBaseUrl(): string {
  const configured = import.meta.env.VITE_CONTROL_PLANE_BASE_URL;
  return typeof configured === 'string' ? configured.replace(/\/$/, '') : '';
}

export interface KairoSpeakRequest {
  event_type: string;
  context?: Record<string, unknown>;
  session_id?: string;
  workspace_id?: string;
  use_runtime?: boolean;
  narration?: 'off' | 'minimal' | 'conversational';
}

export interface KairoSpeakResponse {
  line: string;
  source: 'model' | 'fallback' | 'literal' | 'skipped';
}

export async function postKairoSpeak(body: KairoSpeakRequest): Promise<KairoSpeakResponse> {
  const baseUrl = controlPlaneBaseUrl();
  const url = baseUrl ? `${baseUrl}/api/kairo/speak` : '/api/kairo/speak';
  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    throw new Error(`KAIRO speak failed (${response.status})`);
  }
  return (await response.json()) as KairoSpeakResponse;
}

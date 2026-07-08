export interface KairoTtsResponse {
  available: boolean;
  provider: 'azure' | 'browser';
  audio_base64?: string;
  content_type?: string;
  voice?: string;
}

export async function postKairoTts(text: string, timeoutMs = 2500): Promise<KairoTtsResponse> {
  const baseUrl = import.meta.env.VITE_CONTROL_PLANE_BASE_URL ?? '';
  const url = baseUrl ? `${baseUrl}/api/kairo/tts` : '/api/kairo/tts';
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text }),
      signal: controller.signal,
    });

    if (!response.ok) {
      throw new Error(`kairo tts request failed with status ${response.status}`);
    }

    return response.json() as Promise<KairoTtsResponse>;
  } finally {
    clearTimeout(timeout);
  }
}

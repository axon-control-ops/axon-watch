export interface KairoTtsResponse {
  available: boolean;
  provider: 'azure' | 'browser';
  reason?: string;
  audio_base64?: string;
  content_type?: string;
  voice?: string;
  first_byte_ms?: number;
  prefetch?: boolean;
}

export async function postKairoTts(
  text: string,
  options: {
    timeoutMs?: number;
    rate?: number;
    pitch?: number;
    voice?: string;
  } = {},
): Promise<KairoTtsResponse> {
  // Azure synthesis is allowed 12 seconds server-side. Keep the client budget
  // above that deadline so it receives either audio or synthesis_failed.
  const timeoutMs = options.timeoutMs ?? 15000;
  const baseUrl = import.meta.env.VITE_CONTROL_PLANE_BASE_URL ?? '';
  const url = baseUrl ? `${baseUrl}/api/kairo/tts` : '/api/kairo/tts';
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  const startedAt = performance.now();

  try {
    const response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        text,
        ...(typeof options.rate === 'number' ? { rate: options.rate } : {}),
        ...(typeof options.pitch === 'number' ? { pitch: options.pitch } : {}),
        ...(options.voice ? { voice: options.voice } : {}),
      }),
      signal: controller.signal,
    });

    if (!response.ok) {
      throw new Error(`kairo tts request failed with status ${response.status}`);
    }

    const payload = (await response.json()) as KairoTtsResponse;
    return {
      ...payload,
      first_byte_ms: Math.round(performance.now() - startedAt),
    };
  } finally {
    clearTimeout(timeout);
  }
}

export interface KairoTtsResponse {
  available: boolean;
  provider: 'azure' | 'browser';
  reason?: string;
  audio_base64?: string;
  content_type?: string;
  voice?: string;
  /** Encoded SSML silence before the first spoken phoneme. */
  leading_audio_guard_ms?: number;
  first_byte_ms?: number;
  prefetch?: boolean;
}

/** Sticky until Azure succeeds again — vault_locked / missing_key skip round-trips. */
let azureTtsBlockedReason: string | null = null;
let activeTtsAbort: AbortController | null = null;

export function isAzureTtsBlocked(): boolean {
  return azureTtsBlockedReason === 'vault_locked' || azureTtsBlockedReason === 'missing_key';
}

export function azureTtsBlockedReasonValue(): string | null {
  return azureTtsBlockedReason;
}

/** Cancel an in-flight Azure TTS fetch so barge-in / stand-up can take the lane. */
export function abortActiveKairoTts(): void {
  if (!activeTtsAbort) {
    return;
  }
  activeTtsAbort.abort();
  activeTtsAbort = null;
}

function noteAzureTtsResponse(payload: KairoTtsResponse): void {
  if (payload.available) {
    azureTtsBlockedReason = null;
    return;
  }
  const reason = String(payload.reason || '').trim();
  if (reason === 'vault_locked' || reason === 'missing_key') {
    azureTtsBlockedReason = reason;
  }
}

export async function postKairoTts(
  text: string,
  options: {
    timeoutMs?: number;
    rate?: number;
    pitch?: number;
    voice?: string;
    continuation?: boolean;
  } = {},
): Promise<KairoTtsResponse> {
  // Azure synthesis is allowed 12 seconds server-side. Keep the client budget
  // above that deadline so it receives either audio or synthesis_failed.
  const timeoutMs = options.timeoutMs ?? 15000;
  const baseUrl = import.meta.env.VITE_CONTROL_PLANE_BASE_URL ?? '';
  const url = baseUrl ? `${baseUrl}/api/kairo/tts` : '/api/kairo/tts';
  const controller = new AbortController();
  activeTtsAbort = controller;
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
        ...(options.continuation ? { continuation: true } : {}),
      }),
      signal: controller.signal,
    });

    if (!response.ok) {
      throw new Error(`kairo tts request failed with status ${response.status}`);
    }

    const payload = (await response.json()) as KairoTtsResponse;
    noteAzureTtsResponse(payload);
    return {
      ...payload,
      first_byte_ms: Math.round(performance.now() - startedAt),
    };
  } finally {
    if (activeTtsAbort === controller) {
      activeTtsAbort = null;
    }
    clearTimeout(timeout);
  }
}

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

/** Sticky until Azure succeeds again — vault_locked / missing_key skip round-trips. */
let azureTtsBlockedReason: string | null = null;

export function isAzureTtsBlocked(): boolean {
  return azureTtsBlockedReason === 'vault_locked' || azureTtsBlockedReason === 'missing_key';
}

export function azureTtsBlockedReasonValue(): string | null {
  return azureTtsBlockedReason;
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
    // #region agent log
    fetch('http://127.0.0.1:7706/ingest/90bcaec2-2b39-4d4a-84b5-157c12735440',{method:'POST',headers:{'Content-Type':'application/json','X-Debug-Session-Id':'bef50e'},body:JSON.stringify({sessionId:'bef50e',runId:'heading-audio-before-fix',hypothesisId:'H33,H34',location:'kairo-tts-client.ts:postKairoTts',message:'submitting exact text for speech synthesis',data:{textPreview:text.slice(0,140),textLength:text.length,startsWithWorkInFlight:/^Work in flight\b/i.test(text),rate:options.rate??null,voice:options.voice??null,azureBlocked:azureTtsBlockedReason},timestamp:Date.now()})}).catch(()=>{});
    // #endregion
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
    noteAzureTtsResponse(payload);
    // #region agent log
    fetch('http://127.0.0.1:7706/ingest/90bcaec2-2b39-4d4a-84b5-157c12735440',{method:'POST',headers:{'Content-Type':'application/json','X-Debug-Session-Id':'bef50e'},body:JSON.stringify({sessionId:'bef50e',runId:'narration-sync-fix',hypothesisId:'H46',location:'kairo-tts-client.ts:response',message:'speech synthesis response received',data:{available:payload.available,provider:payload.provider,reason:payload.reason??null,elapsedMs:Math.round(performance.now()-startedAt),textLength:text.length,azureBlocked:azureTtsBlockedReason},timestamp:Date.now()})}).catch(()=>{});
    // #endregion
    return {
      ...payload,
      first_byte_ms: Math.round(performance.now() - startedAt),
    };
  } finally {
    clearTimeout(timeout);
  }
}

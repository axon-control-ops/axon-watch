/**
 * Optional cloud STT adapter behind presence `stt_mode`.
 * Azure cloud is the preferred path; browser Web Speech remains the fallback.
 * Privacy mode blocks both.
 */

export type CloudSttProbe = {
  available: boolean;
  provider: string;
  reason: string | null;
  maxUploadBytes: number;
};

export type CloudSttResult = {
  transcript: string;
  provider: 'azure' | 'browser';
  confidence: number | null;
  reason: string | null;
};

type CloudSttApiResponse = {
  available?: boolean;
  transcript?: string;
  provider?: string;
  confidence?: number | null;
  reason?: string | null;
  max_upload_bytes?: number;
};

let cachedProbe: CloudSttProbe | null = null;

function controlPlaneBaseUrl(): string {
  return import.meta.env.VITE_CONTROL_PLANE_BASE_URL ?? '';
}

function sttUrl(): string {
  const baseUrl = controlPlaneBaseUrl();
  return baseUrl ? `${baseUrl}/api/kairo/stt` : '/api/kairo/stt';
}

function mapApiResponse(payload: CloudSttApiResponse): CloudSttResult {
  const provider = payload.provider === 'azure' ? 'azure' : 'browser';
  return {
    transcript: String(payload.transcript ?? '').trim(),
    provider,
    confidence:
      typeof payload.confidence === 'number' && Number.isFinite(payload.confidence)
        ? payload.confidence
        : null,
    reason: payload.reason ? String(payload.reason) : null,
  };
}

export async function probeCloudSttAvailability(options?: {
  forceRefresh?: boolean;
}): Promise<CloudSttProbe> {
  if (cachedProbe && !options?.forceRefresh) {
    return cachedProbe;
  }
  try {
    const response = await fetch(sttUrl(), { method: 'GET' });
    if (!response.ok) {
      cachedProbe = {
        available: false,
        provider: 'none',
        reason: `stt_unavailable_${response.status}`,
        maxUploadBytes: 0,
      };
      return cachedProbe;
    }
    const payload = (await response.json()) as CloudSttApiResponse;
    cachedProbe = {
      available: Boolean(payload.available),
      provider: String(payload.provider ?? 'none'),
      reason: payload.reason ? String(payload.reason) : null,
      maxUploadBytes: Number(payload.max_upload_bytes ?? 0),
    };
    return cachedProbe;
  } catch {
    cachedProbe = {
      available: false,
      provider: 'none',
      reason: 'stt_unavailable',
      maxUploadBytes: 0,
    };
    return cachedProbe;
  }
}

export async function transcribeCloudStt(
  audioBlob: Blob,
  options: { privacyBlocked?: boolean; language?: string } = {},
): Promise<CloudSttResult> {
  if (options.privacyBlocked) {
    return {
      transcript: '',
      provider: 'browser',
      confidence: null,
      reason: 'privacy_mode',
    };
  }
  if (!audioBlob.size) {
    return {
      transcript: '',
      provider: 'browser',
      confidence: null,
      reason: 'empty_audio',
    };
  }

  const probe = await probeCloudSttAvailability();
  if (!probe.available) {
    return {
      transcript: '',
      provider: 'browser',
      confidence: null,
      reason: probe.reason ?? 'cloud_stt_not_configured',
    };
  }

  const language = (options.language ?? 'en-US').trim() || 'en-US';
  const extension = audioBlob.type.includes('wav')
    ? 'wav'
    : audioBlob.type.includes('webm')
      ? 'webm'
      : 'ogg';
  const form = new FormData();
  form.append('file', audioBlob, `capture.${extension}`);

  try {
    const response = await fetch(`${sttUrl()}?language=${encodeURIComponent(language)}`, {
      method: 'POST',
      body: form,
    });
    if (!response.ok) {
      return {
        transcript: '',
        provider: 'browser',
        confidence: null,
        reason: `stt_unavailable_${response.status}`,
      };
    }
    const payload = (await response.json()) as CloudSttApiResponse;
    const mapped = mapApiResponse(payload);
    if (!payload.available) {
      return {
        ...mapped,
        provider: 'browser',
        reason: mapped.reason ?? 'cloud_stt_unavailable',
      };
    }
    return mapped;
  } catch {
    return {
      transcript: '',
      provider: 'browser',
      confidence: null,
      reason: 'stt_unavailable',
    };
  }
}

export function resolveSttCaptureMode(
  sttMode: string | null | undefined,
  privacyBlocked: boolean,
): 'browser' | 'browser_continuous' | 'cloud' | 'blocked' {
  if (privacyBlocked) {
    return 'blocked';
  }
  if (sttMode === 'browser_continuous') {
    return 'browser_continuous';
  }
  if (sttMode === 'cloud') {
    return 'cloud';
  }
  return 'browser';
}

export function clearCloudSttProbeCache(): void {
  cachedProbe = null;
}

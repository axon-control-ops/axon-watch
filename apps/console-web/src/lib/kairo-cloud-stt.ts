/**
 * Optional cloud STT adapter behind presence `stt_mode`.
 * Browser Web Speech remains the default and fallback; privacy mode blocks both.
 */

export type CloudSttResult = {
  transcript: string;
  provider: 'cloud' | 'browser_fallback';
  reason: string | null;
};

export async function transcribeCloudStt(
  _audioBlob: Blob,
  options: { privacyBlocked?: boolean } = {},
): Promise<CloudSttResult> {
  if (options.privacyBlocked) {
    return {
      transcript: '',
      provider: 'browser_fallback',
      reason: 'privacy_mode',
    };
  }
  // Cloud STT endpoint is optional; fall back until configured.
  const baseUrl = import.meta.env.VITE_CONTROL_PLANE_BASE_URL ?? '';
  const url = baseUrl ? `${baseUrl}/api/kairo/stt` : '/api/kairo/stt';
  try {
    const response = await fetch(url, { method: 'GET' });
    if (!response.ok) {
      return {
        transcript: '',
        provider: 'browser_fallback',
        reason: `stt_unavailable_${response.status}`,
      };
    }
  } catch {
    return {
      transcript: '',
      provider: 'browser_fallback',
      reason: 'stt_unavailable',
    };
  }
  return {
    transcript: '',
    provider: 'browser_fallback',
    reason: 'cloud_stt_not_configured',
  };
}

export function resolveSttCaptureMode(
  sttMode: string | null | undefined,
  privacyBlocked: boolean,
): 'browser' | 'browser_continuous' | 'blocked' {
  if (privacyBlocked) {
    return 'blocked';
  }
  if (sttMode === 'browser_continuous') {
    return 'browser_continuous';
  }
  // cloud still uses browser capture today; cloud adapter is optional post-process.
  return 'browser';
}

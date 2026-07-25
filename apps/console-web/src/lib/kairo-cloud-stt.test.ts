import { afterEach, describe, expect, it, vi } from 'vitest';

import {
  clearCloudSttProbeCache,
  probeCloudSttAvailability,
  resolveSttCaptureMode,
  transcribeCloudStt,
} from './kairo-cloud-stt';

describe('resolveSttCaptureMode', () => {
  it('blocks when privacy is on', () => {
    expect(resolveSttCaptureMode('cloud', true)).toBe('blocked');
  });

  it('maps continuous, cloud, and browser modes', () => {
    expect(resolveSttCaptureMode('browser_continuous', false)).toBe('browser_continuous');
    expect(resolveSttCaptureMode('cloud', false)).toBe('cloud');
    expect(resolveSttCaptureMode('browser', false)).toBe('browser');
  });
});

describe('transcribeCloudStt', () => {
  afterEach(() => {
    clearCloudSttProbeCache();
    vi.restoreAllMocks();
  });

  it('returns privacy reason without uploading', async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal('fetch', fetchMock);
    const result = await transcribeCloudStt(new Blob(['x']), { privacyBlocked: true });
    expect(result.reason).toBe('privacy_mode');
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('posts audio when cloud probe is available', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          available: true,
          provider: 'azure',
          max_upload_bytes: 2048,
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          available: true,
          transcript: 'check tunnel status',
          provider: 'azure',
          confidence: 0.87,
          reason: null,
        }),
      });
    vi.stubGlobal('fetch', fetchMock);

    const result = await transcribeCloudStt(new Blob(['audio-bytes'], { type: 'audio/ogg' }));
    expect(result.transcript).toBe('check tunnel status');
    expect(result.provider).toBe('azure');
    expect(result.confidence).toBe(0.87);
    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(String(fetchMock.mock.calls[1]?.[0])).toContain('/api/kairo/stt?language=en-US');
  });

  it('falls back when probe reports unavailable', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          available: false,
          provider: 'none',
          reason: 'azure_speech_not_configured',
        }),
      }),
    );
    const result = await transcribeCloudStt(new Blob(['audio']));
    expect(result.provider).toBe('browser');
    expect(result.reason).toBe('azure_speech_not_configured');
  });
});

describe('probeCloudSttAvailability', () => {
  afterEach(() => {
    clearCloudSttProbeCache();
    vi.restoreAllMocks();
  });

  it('caches probe responses', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ available: true, provider: 'azure', max_upload_bytes: 1024 }),
    });
    vi.stubGlobal('fetch', fetchMock);
    const first = await probeCloudSttAvailability();
    const second = await probeCloudSttAvailability();
    expect(first.available).toBe(true);
    expect(second.available).toBe(true);
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
});

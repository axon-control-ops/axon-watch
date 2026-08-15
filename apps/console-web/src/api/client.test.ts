import { afterEach, describe, expect, it, vi } from 'vitest';

import { fetchJson, fetchWithTimeout } from './client';

describe('fetchJson timeout', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.useRealTimers();
  });

  it('rejects when the request exceeds the timeout budget', async () => {
    vi.useFakeTimers();
    vi.stubGlobal(
      'fetch',
      vi.fn((_url: string, init?: RequestInit) => {
        return new Promise((_resolve, reject) => {
          init?.signal?.addEventListener('abort', () => {
            reject(new DOMException('Aborted', 'AbortError'));
          });
        });
      }),
    );

    const pending = fetchJson('/api/runtime/summary', {}, 'runtime summary request failed', 50);
    const expectation = expect(pending).rejects.toThrow(/timed out|runtime summary request failed/);
    await vi.advanceTimersByTimeAsync(60);
    await expectation;
  });

  it('rethrows AbortError when the caller cancels via init.signal', async () => {
    const controller = new AbortController();
    vi.stubGlobal(
      'fetch',
      vi.fn((_url: string, init?: RequestInit) => {
        return new Promise((_resolve, reject) => {
          init?.signal?.addEventListener('abort', () => {
            reject(new DOMException('Aborted', 'AbortError'));
          });
        });
      }),
    );

    const pending = fetchJson(
      '/api/runtime/summary',
      { signal: controller.signal },
      'runtime summary request failed',
      5_000,
    );
    const expectation = expect(pending).rejects.toMatchObject({ name: 'AbortError' });
    controller.abort();
    await expectation;
  });

  it('surfaces control-plane detail on non-OK responses', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => ({
        ok: false,
        status: 403,
        json: async () => ({
          detail: 'cross-origin mutation blocked (origin http://127.0.0.1:5173 != https://axon.example.com)',
          csrf_blocked: true,
        }),
      })),
    );

    await expect(fetchJson('/api/chat/messages', { method: 'POST' }, 'chat message submit failed')).rejects.toThrow(
      /chat message submit failed: cross-origin mutation blocked/,
    );
  });
});

describe('fetchWithTimeout', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.useRealTimers();
  });

  it('rejects instead of hanging forever when the network stalls', async () => {
    // Regression: several callers used bare fetch() with no signal, so a
    // stalled (not failed) connection left the request pending forever with
    // no error and no recovery — e.g. tunnel start/stop, attachment upload,
    // inbox acknowledge, Sentry resolve/attend.
    vi.useFakeTimers();
    vi.stubGlobal(
      'fetch',
      vi.fn((_url: string, init?: RequestInit) => {
        return new Promise((_resolve, reject) => {
          init?.signal?.addEventListener('abort', () => {
            reject(new DOMException('Aborted', 'AbortError'));
          });
        });
      }),
    );

    const pending = fetchWithTimeout('/api/tunnel/start', { method: 'POST' }, 50);
    const expectation = expect(pending).rejects.toThrow(/timed out/);
    await vi.advanceTimersByTimeAsync(60);
    await expectation;
  });

  it('resolves with the raw Response so callers can branch on status themselves', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => ({ ok: false, status: 404, text: async () => 'not found' })),
    );

    const response = await fetchWithTimeout('/api/inbox/signals/acknowledge', { method: 'POST' });
    expect(response.ok).toBe(false);
    expect(response.status).toBe(404);
  });
});

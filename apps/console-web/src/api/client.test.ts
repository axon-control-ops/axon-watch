import { afterEach, describe, expect, it, vi } from 'vitest';

import { fetchJson } from './client';

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
});

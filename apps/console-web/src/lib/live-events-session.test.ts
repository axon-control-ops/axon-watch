import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import {
  buildLiveEventsUrl,
  parseLiveEventData,
  shouldTriggerRefresh,
  startLiveEventsSession,
} from './live-events-session';

describe('live events session helpers', () => {
  it('builds a proxied live events URL when no base URL is configured', () => {
    expect(buildLiveEventsUrl('')).toBe('/api/live/events');
  });

  it('builds an absolute live events URL from an explicit base URL', () => {
    expect(buildLiveEventsUrl('http://127.0.0.1:8787/')).toBe(
      'http://127.0.0.1:8787/api/live/events',
    );
  });

  it('parses connected and runtime_refresh payloads', () => {
    expect(parseLiveEventData('{"type":"connected"}')).toEqual({ type: 'connected' });
    expect(parseLiveEventData('{"type":"runtime_refresh"}')).toEqual({
      type: 'runtime_refresh',
    });
    expect(parseLiveEventData('{"type":"unknown"}')).toBeNull();
    expect(parseLiveEventData('not-json')).toBeNull();
  });

  it('only triggers refresh for runtime_refresh events', () => {
    expect(shouldTriggerRefresh({ type: 'connected' })).toBe(false);
    expect(shouldTriggerRefresh({ type: 'runtime_refresh' })).toBe(true);
  });
});

describe('startLiveEventsSession', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('invokes refresh on runtime_refresh SSE messages', () => {
    const onRefresh = vi.fn();
    let messageHandler: ((event: MessageEvent) => void) | null = null;

    class MockEventSource {
      onmessage: ((event: MessageEvent) => void) | null = null;
      onerror: (() => void) | null = null;

      constructor(_url: string) {
        messageHandler = (event) => {
          this.onmessage?.(event);
        };
      }

      close(): void {}
    }

    const session = startLiveEventsSession({
      onRefresh,
      EventSourceImpl: MockEventSource as unknown as typeof EventSource,
      documentRef: {
        visibilityState: 'visible',
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
      },
    });

    expect(messageHandler).not.toBeNull();
    messageHandler!({ data: '{"type":"connected"}' } as MessageEvent);
    expect(onRefresh).not.toHaveBeenCalled();

    messageHandler!({ data: '{"type":"runtime_refresh"}' } as MessageEvent);
    expect(onRefresh).toHaveBeenCalledTimes(1);

    session.disconnect();
  });

  it('falls back to visibility-aware polling when EventSource construction fails', () => {
    const onRefresh = vi.fn();

    const session = startLiveEventsSession({
      onRefresh,
      pollIntervalMs: 30_000,
      EventSourceImpl: (() => {
        throw new Error('EventSource unavailable');
      }) as unknown as typeof EventSource,
      documentRef: {
        visibilityState: 'visible',
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
      },
    });

    vi.advanceTimersByTime(30_000);
    expect(onRefresh).toHaveBeenCalledTimes(1);

    session.disconnect();
    vi.advanceTimersByTime(30_000);
    expect(onRefresh).toHaveBeenCalledTimes(1);
  });
});

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import {
  buildLiveEventsUrl,
  parseLiveEventData,
  shouldTriggerPresenceRefresh,
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

  it('parses connected, runtime_refresh, presence_refresh, and spoken_briefing payloads', () => {
    expect(parseLiveEventData('{"type":"connected"}')).toEqual({ type: 'connected' });
    expect(parseLiveEventData('{"type":"runtime_refresh"}')).toEqual({
      type: 'runtime_refresh',
    });
    expect(parseLiveEventData('{"type":"presence_refresh"}')).toEqual({
      type: 'presence_refresh',
    });
    expect(parseLiveEventData('{"type":"spoken_briefing"}')).toEqual({
      type: 'spoken_briefing',
    });
    expect(parseLiveEventData('{"type":"unknown"}')).toBeNull();
    expect(parseLiveEventData('not-json')).toBeNull();
  });

  it('routes refresh kinds to the correct handlers', () => {
    expect(shouldTriggerRefresh({ type: 'connected' })).toBe(false);
    expect(shouldTriggerRefresh({ type: 'runtime_refresh' })).toBe(true);
    expect(shouldTriggerPresenceRefresh({ type: 'presence_refresh' })).toBe(true);
    expect(shouldTriggerPresenceRefresh({ type: 'runtime_refresh' })).toBe(false);
  });
});

describe('startLiveEventsSession', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('invokes presence refresh separately from runtime refresh', () => {
    const onRefresh = vi.fn();
    const onPresenceRefresh = vi.fn().mockResolvedValue(undefined);
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
      onPresenceRefresh,
      EventSourceImpl: MockEventSource as unknown as typeof EventSource,
      documentRef: {
        visibilityState: 'visible',
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
      },
    });

    messageHandler!({ data: '{"type":"presence_refresh"}' } as MessageEvent);
    expect(onPresenceRefresh).toHaveBeenCalledTimes(1);
    expect(onRefresh).not.toHaveBeenCalled();

    messageHandler!({ data: '{"type":"runtime_refresh"}' } as MessageEvent);
    expect(onRefresh).toHaveBeenCalledTimes(1);

    session.disconnect();
  });

  it('skips presence refresh while the document is hidden', async () => {
    const onPresenceRefresh = vi.fn().mockResolvedValue(undefined);
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
      onRefresh: vi.fn(),
      onPresenceRefresh,
      EventSourceImpl: MockEventSource as unknown as typeof EventSource,
      documentRef: {
        visibilityState: 'hidden',
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
      },
    });

    messageHandler!({ data: '{"type":"presence_refresh"}' } as MessageEvent);
    await Promise.resolve();
    expect(onPresenceRefresh).not.toHaveBeenCalled();

    session.disconnect();
  });

  it('dedupes overlapping presence refresh handlers', async () => {
    let resolveRefresh: () => void = () => {};
    const onPresenceRefresh = vi.fn(
      () =>
        new Promise<void>((resolve) => {
          resolveRefresh = resolve;
        }),
    );
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
      onRefresh: vi.fn(),
      onPresenceRefresh,
      EventSourceImpl: MockEventSource as unknown as typeof EventSource,
      documentRef: {
        visibilityState: 'visible',
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
      },
    });

    messageHandler!({ data: '{"type":"presence_refresh"}' } as MessageEvent);
    messageHandler!({ data: '{"type":"presence_refresh"}' } as MessageEvent);
    await Promise.resolve();
    expect(onPresenceRefresh).toHaveBeenCalledTimes(1);

    resolveRefresh();
    await Promise.resolve();

    messageHandler!({ data: '{"type":"presence_refresh"}' } as MessageEvent);
    await Promise.resolve();
    expect(onPresenceRefresh).toHaveBeenCalledTimes(2);

    session.disconnect();
  });

  it('routes spoken_briefing events to the spoken briefing handler', async () => {
    const onSpokenBriefing = vi.fn();
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
      onRefresh: vi.fn(),
      onSpokenBriefing,
      EventSourceImpl: MockEventSource as unknown as typeof EventSource,
      documentRef: {
        visibilityState: 'visible',
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
      },
    });

    messageHandler!({ data: '{"type":"spoken_briefing"}' } as MessageEvent);
    await Promise.resolve();
    expect(onSpokenBriefing).toHaveBeenCalledTimes(1);
    session.disconnect();
  });

  it('skips runtime refresh while the document is hidden', async () => {
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
        visibilityState: 'hidden',
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
      },
    });

    messageHandler!({ data: '{"type":"runtime_refresh"}' } as MessageEvent);
    await Promise.resolve();
    expect(onRefresh).not.toHaveBeenCalled();

    session.disconnect();
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

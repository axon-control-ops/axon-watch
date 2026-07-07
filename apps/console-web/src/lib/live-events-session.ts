export type LiveEventType = 'connected' | 'runtime_refresh' | 'presence_refresh';

export interface LiveEventPayload {
  type: LiveEventType;
}

const DEFAULT_POLL_INTERVAL_MS = 30_000;

function controlPlaneBaseUrl(): string {
  const configured = import.meta.env.VITE_CONTROL_PLANE_BASE_URL;
  if (configured) {
    return configured.replace(/\/$/, '');
  }

  return '';
}

export function buildLiveEventsUrl(baseUrl?: string): string {
  const normalized = (baseUrl ?? controlPlaneBaseUrl()).replace(/\/$/, '');
  return normalized ? `${normalized}/api/live/events` : '/api/live/events';
}

export function parseLiveEventData(raw: string): LiveEventPayload | null {
  const trimmed = raw.trim();
  if (!trimmed) {
    return null;
  }

  try {
    const parsed = JSON.parse(trimmed) as LiveEventPayload;
    if (parsed.type === 'connected' || parsed.type === 'runtime_refresh' || parsed.type === 'presence_refresh') {
      return parsed;
    }
  } catch {
    return null;
  }

  return null;
}

export function shouldTriggerRefresh(event: LiveEventPayload): boolean {
  return event.type === 'runtime_refresh';
}

export function shouldTriggerPresenceRefresh(event: LiveEventPayload): boolean {
  return event.type === 'presence_refresh';
}

export interface LiveEventsSessionOptions {
  onRefresh: () => void | Promise<void>;
  onPresenceRefresh?: () => void | Promise<void>;
  pollIntervalMs?: number;
  EventSourceImpl?: typeof EventSource;
  documentRef?: Pick<Document, 'visibilityState' | 'addEventListener' | 'removeEventListener'>;
}

export interface LiveEventsSession {
  disconnect: () => void;
}

function isDocumentVisible(
  documentRef: Pick<Document, 'visibilityState'>,
): boolean {
  return documentRef.visibilityState === 'visible';
}

export function startLiveEventsSession(options: LiveEventsSessionOptions): LiveEventsSession {
  const pollIntervalMs = options.pollIntervalMs ?? DEFAULT_POLL_INTERVAL_MS;
  const EventSourceImpl = options.EventSourceImpl ?? EventSource;
  const documentRef = options.documentRef ?? document;

  let eventSource: EventSource | null = null;
  let pollTimer: ReturnType<typeof setInterval> | null = null;
  let refreshInFlight = false;
  let presenceRefreshInFlight = false;
  let disconnected = false;

  async function invokeRefresh(): Promise<void> {
    if (refreshInFlight || disconnected || !isDocumentVisible(documentRef)) {
      return;
    }

    refreshInFlight = true;
    try {
      await options.onRefresh();
    } finally {
      refreshInFlight = false;
    }
  }

  async function invokePresenceRefresh(): Promise<void> {
    if (
      presenceRefreshInFlight ||
      disconnected ||
      !options.onPresenceRefresh ||
      !isDocumentVisible(documentRef)
    ) {
      return;
    }

    presenceRefreshInFlight = true;
    try {
      await options.onPresenceRefresh();
    } finally {
      presenceRefreshInFlight = false;
    }
  }

  function stopPolling(): void {
    if (pollTimer !== null) {
      clearInterval(pollTimer);
      pollTimer = null;
    }
  }

  function startPolling(): void {
    if (pollTimer !== null || disconnected) {
      return;
    }

    pollTimer = setInterval(() => {
      if (documentRef.visibilityState === 'visible') {
        void invokeRefresh();
      }
    }, pollIntervalMs);
  }

  function handleMessage(raw: string): void {
    const event = parseLiveEventData(raw);
    if (!event) {
      return;
    }
    if (shouldTriggerPresenceRefresh(event)) {
      void invokePresenceRefresh();
      return;
    }
    if (shouldTriggerRefresh(event)) {
      void invokeRefresh();
    }
  }

  function onVisibilityChange(): void {
    if (!isDocumentVisible(documentRef)) {
      return;
    }
    if (pollTimer !== null) {
      void invokeRefresh();
      return;
    }
    void invokePresenceRefresh();
  }

  function disconnectEventSource(): void {
    if (eventSource) {
      eventSource.close();
      eventSource = null;
    }
  }

  function connectEventSource(): void {
    if (disconnected || typeof EventSourceImpl !== 'function') {
      startPolling();
      return;
    }

    disconnectEventSource();

    try {
      eventSource = new EventSourceImpl(buildLiveEventsUrl());
    } catch {
      startPolling();
      return;
    }

    eventSource.onmessage = (message) => {
      handleMessage(String(message.data ?? ''));
    };

    eventSource.onerror = () => {
      disconnectEventSource();
      startPolling();
    };
  }

  connectEventSource();
  documentRef.addEventListener('visibilitychange', onVisibilityChange);

  return {
    disconnect(): void {
      if (disconnected) {
        return;
      }

      disconnected = true;
      disconnectEventSource();
      stopPolling();
      documentRef.removeEventListener('visibilitychange', onVisibilityChange);
    },
  };
}

export type LiveEventType =
  | 'connected'
  | 'runtime_refresh'
  | 'presence_refresh'
  | 'spoken_briefing'
  /** Lead / specialist rollup with an explicit speakable line. */
  | 'spoken_line'
  /** Material event invalidation — proactive advise, not timer heartbeats. */
  | 'material_change';

export interface LiveEventPayload {
  type: LiveEventType;
  /** Optional receipt / signal id for proactive speech dedupe. */
  receipt_id?: string;
  signal_id?: string;
  /** Present on `spoken_line` — literal TTS copy. */
  line?: string;
  workspace_id?: string;
  kind?: string;
  speaker_name?: string;
  speaker_role?: string;
  speaker_employee_id?: string;
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
    if (
      parsed.type === 'connected' ||
      parsed.type === 'runtime_refresh' ||
      parsed.type === 'presence_refresh' ||
      parsed.type === 'spoken_briefing' ||
      parsed.type === 'spoken_line' ||
      parsed.type === 'material_change'
    ) {
      return parsed;
    }
  } catch {
    return null;
  }

  return null;
}

export function shouldTriggerRefresh(event: LiveEventPayload): boolean {
  return event.type === 'runtime_refresh' || event.type === 'material_change';
}

export function shouldTriggerPresenceRefresh(event: LiveEventPayload): boolean {
  return event.type === 'presence_refresh' || event.type === 'material_change';
}

export function shouldTriggerSpokenBriefing(event: LiveEventPayload): boolean {
  // Spoken interrupts are explicit only. material_change refreshes quietly.
  return event.type === 'spoken_briefing';
}

export function shouldTriggerSpokenLine(event: LiveEventPayload): boolean {
  return event.type === 'spoken_line' && Boolean(event.line?.trim());
}

export interface LiveEventsSessionOptions {
  onRefresh: () => void | Promise<void>;
  onResync?: () => void | Promise<void>;
  onPresenceRefresh?: () => void | Promise<void>;
  onSpokenBriefing?: () => void | Promise<void>;
  /** Lead takeover / synthesis — speak the provided line as that teammate. */
  onSpokenLine?: (event: LiveEventPayload) => void | Promise<void>;
  /** Lead rollups / review_ready — refresh engagement surfaces without speaking. */
  onMaterialChange?: () => void | Promise<void>;
  pollIntervalMs?: number;
  reconnectBackoffMs?: number[];
  EventSourceImpl?: typeof EventSource;
  documentRef?: Pick<Document, 'visibilityState' | 'addEventListener' | 'removeEventListener'>;
}

export interface LiveEventsSession {
  disconnect: () => void;
}

export type LiveEventsTelemetry = {
  connection_count: number;
  disconnect_count: number;
  reconnect_count: number;
  last_event_at: number | null;
  last_resync_at: number | null;
};

const DEFAULT_RECONNECT_BACKOFF_MS = [1000, 2000, 4000, 8000, 16000];

let telemetry: LiveEventsTelemetry = {
  connection_count: 0,
  disconnect_count: 0,
  reconnect_count: 0,
  last_event_at: null,
  last_resync_at: null,
};

export function getLiveEventsTelemetry(): LiveEventsTelemetry {
  return { ...telemetry };
}

export function resetLiveEventsTelemetryForTests(): void {
  telemetry = {
    connection_count: 0,
    disconnect_count: 0,
    reconnect_count: 0,
    last_event_at: null,
    last_resync_at: null,
  };
}

function isDocumentVisible(
  documentRef: Pick<Document, 'visibilityState'>,
): boolean {
  return documentRef.visibilityState === 'visible';
}

export function startLiveEventsSession(options: LiveEventsSessionOptions): LiveEventsSession {
  const pollIntervalMs = options.pollIntervalMs ?? DEFAULT_POLL_INTERVAL_MS;
  const reconnectBackoffMs = options.reconnectBackoffMs ?? DEFAULT_RECONNECT_BACKOFF_MS;
  const EventSourceImpl = options.EventSourceImpl ?? EventSource;
  const documentRef = options.documentRef ?? document;

  let eventSource: EventSource | null = null;
  let pollTimer: ReturnType<typeof setInterval> | null = null;
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  let refreshInFlight = false;
  let presenceRefreshInFlight = false;
  let materialChangeInFlight = false;
  let resyncInFlight = false;
  let disconnected = false;
  let reconnectAttempt = 0;

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

  async function invokeMaterialChange(): Promise<void> {
    if (
      materialChangeInFlight ||
      disconnected ||
      !options.onMaterialChange ||
      !isDocumentVisible(documentRef)
    ) {
      return;
    }

    materialChangeInFlight = true;
    try {
      await options.onMaterialChange();
    } finally {
      materialChangeInFlight = false;
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

  async function invokeResync(): Promise<void> {
    if (resyncInFlight || disconnected || !isDocumentVisible(documentRef)) {
      return;
    }
    resyncInFlight = true;
    telemetry.last_resync_at = Date.now();
    try {
      await (options.onResync ?? options.onRefresh)();
    } finally {
      resyncInFlight = false;
    }
  }

  function handleMessage(raw: string): void {
    const event = parseLiveEventData(raw);
    if (!event) {
      return;
    }
    telemetry.last_event_at = Date.now();
    if (event.type === 'connected') {
      reconnectAttempt = 0;
    }
    if (shouldTriggerSpokenBriefing(event)) {
      void options.onSpokenBriefing?.();
      return;
    }
    if (shouldTriggerSpokenLine(event)) {
      void options.onSpokenLine?.(event);
      // Keep engagement surfaces current while the Lead speaks.
      if (options.onMaterialChange) {
        void invokeMaterialChange();
      }
      return;
    }
    if (event.type === 'material_change' && options.onMaterialChange) {
      void invokeMaterialChange();
      return;
    }
    if (shouldTriggerPresenceRefresh(event)) {
      void invokePresenceRefresh();
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

  function stopReconnect(): void {
    if (reconnectTimer !== null) {
      clearTimeout(reconnectTimer);
      reconnectTimer = null;
    }
  }

  function scheduleReconnect(): void {
    if (disconnected || reconnectTimer !== null) {
      return;
    }
    if (reconnectAttempt >= reconnectBackoffMs.length) {
      startPolling();
      return;
    }
    const delay = reconnectBackoffMs[reconnectAttempt] ?? reconnectBackoffMs[reconnectBackoffMs.length - 1];
    reconnectTimer = setTimeout(() => {
      reconnectTimer = null;
      reconnectAttempt += 1;
      telemetry.reconnect_count += 1;
      connectEventSource();
      void invokeResync();
    }, delay);
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
      telemetry.connection_count += 1;
    } catch {
      startPolling();
      return;
    }

    eventSource.onmessage = (message) => {
      handleMessage(String(message.data ?? ''));
    };

    eventSource.onerror = () => {
      telemetry.disconnect_count += 1;
      disconnectEventSource();
      scheduleReconnect();
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
      stopReconnect();
      documentRef.removeEventListener('visibilitychange', onVisibilityChange);
    },
  };
}

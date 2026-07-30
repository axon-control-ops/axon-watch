import type { ChatUiAction } from './chat-ui-action';

export type ChatStreamEventType =
  | 'connected'
  | 'chat_stream_delta'
  | 'chat_stream_milestone'
  | 'chat_stream_done'
  | 'chat_stream_error'
  | 'chat_stream_close';

export interface ChatStreamEventPayload {
  type: ChatStreamEventType;
  thread_id?: string;
  message_id?: string;
  content?: string;
  delta?: string;
  error?: string;
  dispatched?: boolean;
  run_id?: string;
  system_message_id?: string;
  system_content?: string;
  ui_action?: ChatUiAction | null;
  event_key?: string;
  event_type?: string;
  context?: Record<string, unknown>;
  attachments?: Array<{
    attachment_id: string;
    filename: string;
    mime_type: string;
    url: string;
  }>;
}

function controlPlaneBaseUrl(): string {
  const configured = import.meta.env.VITE_CONTROL_PLANE_BASE_URL;
  if (configured) {
    return configured.replace(/\/$/, '');
  }

  return '';
}

export function buildChatStreamUrl(threadId: string, baseUrl?: string): string {
  const normalized = (baseUrl ?? controlPlaneBaseUrl()).replace(/\/$/, '');
  const encodedThreadId = encodeURIComponent(threadId);
  return normalized
    ? `${normalized}/api/chat/threads/${encodedThreadId}/stream`
    : `/api/chat/threads/${encodedThreadId}/stream`;
}

export function parseChatStreamEventData(raw: string): ChatStreamEventPayload | null {
  const trimmed = raw.trim();
  if (!trimmed) {
    return null;
  }

  try {
    const parsed = JSON.parse(trimmed) as ChatStreamEventPayload;
    if (!parsed.type) {
      return null;
    }
    return parsed;
  } catch {
    return null;
  }
}

/** Transient SSE drops are common when switching workspaces (browser connection caps). */
export const CHAT_STREAM_RECONNECT_MAX_ATTEMPTS = 8;
export const CHAT_STREAM_RECONNECT_BASE_MS = 400;

export interface ChatStreamSessionOptions {
  threadId: string;
  messageId: string;
  onDelta: (content: string) => void;
  onMilestone?: (payload: ChatStreamEventPayload) => void;
  onDone?: (payload: ChatStreamEventPayload) => void;
  onError?: (message: string, payload?: ChatStreamEventPayload) => void;
  EventSourceImpl?: typeof EventSource;
  /** Optional delay helper for tests. */
  sleep?: (ms: number) => Promise<void>;
  maxReconnectAttempts?: number;
  reconnectBaseMs?: number;
}

export interface ChatStreamSession {
  disconnect: () => void;
}

export function startChatStreamSession(options: ChatStreamSessionOptions): ChatStreamSession {
  const EventSourceImpl = options.EventSourceImpl ?? EventSource;
  const maxReconnectAttempts =
    options.maxReconnectAttempts ?? CHAT_STREAM_RECONNECT_MAX_ATTEMPTS;
  const reconnectBaseMs = options.reconnectBaseMs ?? CHAT_STREAM_RECONNECT_BASE_MS;
  let eventSource: EventSource | null = null;
  let disconnected = false;
  let reconnectAttempts = 0;
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  let terminal = false;
  let settled = false;
  /** True once we saw a delta for this message — quiet close then means cut-off, not cold fail. */
  let sawMessageDelta = false;

  function clearReconnectTimer(): void {
    if (reconnectTimer !== null) {
      clearTimeout(reconnectTimer);
      reconnectTimer = null;
    }
  }

  function disconnectEventSource(): void {
    if (eventSource) {
      eventSource.onmessage = null;
      eventSource.onerror = null;
      eventSource.close();
      eventSource = null;
    }
  }

  function fail(message: string, payload?: ChatStreamEventPayload): void {
    if (terminal || disconnected || settled) {
      return;
    }
    terminal = true;
    settled = true;
    clearReconnectTimer();
    disconnectEventSource();
    options.onError?.(message, payload);
  }

  function connectEventSource(): void {
    if (disconnected || terminal) {
      return;
    }
    disconnectEventSource();
    try {
      eventSource = new EventSourceImpl(buildChatStreamUrl(options.threadId));
    } catch (error) {
      fail(error instanceof Error ? error.message : 'chat stream connection failed');
      return;
    }

    eventSource.onmessage = (message) => {
      const payload = parseChatStreamEventData(String(message.data ?? ''));
      if (!payload || disconnected || terminal) {
        return;
      }

      if (payload.type === 'connected') {
        return;
      }

      if (payload.type === 'chat_stream_delta' && payload.message_id === options.messageId) {
        reconnectAttempts = 0;
        sawMessageDelta = true;
        options.onDelta(String(payload.content ?? ''));
        return;
      }

      if (payload.type === 'chat_stream_done' && payload.message_id === options.messageId) {
        reconnectAttempts = 0;
        options.onDelta(String(payload.content ?? ''));
        terminal = true;
        settled = true;
        clearReconnectTimer();
        try {
          options.onDone?.(payload);
        } finally {
          disconnectEventSource();
        }
        return;
      }

      if (payload.type === 'chat_stream_milestone' && payload.message_id === options.messageId) {
        options.onMilestone?.(payload);
        return;
      }

      if (payload.type === 'chat_stream_error' && payload.message_id === options.messageId) {
        options.onDelta(String(payload.content ?? payload.error ?? 'stream failed'));
        fail(String(payload.error ?? payload.content ?? 'stream failed'), payload);
        return;
      }

      if (payload.type === 'chat_stream_close') {
        // Quiet end of stream job. Prefer done/error when present; otherwise settle
        // so Ask/plan chrome does not stick active after the hub closes.
        terminal = true;
        clearReconnectTimer();
        disconnectEventSource();
        if (!settled && !disconnected) {
          settled = true;
          // Distinguish cold close (never started streaming) from mid-run drop so
          // voice / Soft Attention do not claim the run "couldn't start".
          options.onError?.(
            sawMessageDelta ? 'chat stream interrupted' : 'chat stream closed',
          );
        }
      }
    };

    eventSource.onerror = () => {
      if (disconnected || terminal) {
        disconnectEventSource();
        return;
      }
      disconnectEventSource();
      if (reconnectAttempts >= maxReconnectAttempts) {
        fail('chat stream disconnected');
        return;
      }
      const delayMs = reconnectBaseMs * 2 ** reconnectAttempts;
      reconnectAttempts += 1;
      clearReconnectTimer();
      reconnectTimer = setTimeout(() => {
        reconnectTimer = null;
        connectEventSource();
      }, delayMs);
    };
  }

  connectEventSource();

  return {
    disconnect(): void {
      if (disconnected) {
        return;
      }
      disconnected = true;
      clearReconnectTimer();
      disconnectEventSource();
    },
  };
}

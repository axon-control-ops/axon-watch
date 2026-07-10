import type { ChatUiAction } from './chat-ui-action';

export type ChatStreamEventType =
  | 'connected'
  | 'chat_stream_delta'
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

export interface ChatStreamSessionOptions {
  threadId: string;
  messageId: string;
  onDelta: (content: string) => void;
  onDone?: (payload: ChatStreamEventPayload) => void;
  onError?: (message: string, payload?: ChatStreamEventPayload) => void;
  EventSourceImpl?: typeof EventSource;
}

export interface ChatStreamSession {
  disconnect: () => void;
}

export function startChatStreamSession(options: ChatStreamSessionOptions): ChatStreamSession {
  const EventSourceImpl = options.EventSourceImpl ?? EventSource;
  let eventSource: EventSource | null = null;
  let disconnected = false;

  function disconnectEventSource(): void {
    if (eventSource) {
      eventSource.close();
      eventSource = null;
    }
  }

  try {
    eventSource = new EventSourceImpl(buildChatStreamUrl(options.threadId));
  } catch (error) {
    options.onError?.(
      error instanceof Error ? error.message : 'chat stream connection failed',
    );
    return { disconnect(): void {} };
  }

  eventSource.onmessage = (message) => {
    const payload = parseChatStreamEventData(String(message.data ?? ''));
    if (!payload) {
      return;
    }

    if (payload.type === 'chat_stream_delta' && payload.message_id === options.messageId) {
      options.onDelta(String(payload.content ?? ''));
      return;
    }

    if (payload.type === 'chat_stream_done' && payload.message_id === options.messageId) {
      options.onDelta(String(payload.content ?? ''));
      options.onDone?.(payload);
      disconnectEventSource();
      return;
    }

    if (payload.type === 'chat_stream_error' && payload.message_id === options.messageId) {
      options.onDelta(String(payload.content ?? payload.error ?? 'stream failed'));
      options.onError?.(
        String(payload.error ?? payload.content ?? 'stream failed'),
        payload,
      );
      disconnectEventSource();
    }

    if (payload.type === 'chat_stream_close') {
      disconnectEventSource();
    }
  };

  eventSource.onerror = () => {
    if (!disconnected) {
      options.onError?.('chat stream disconnected');
    }
    disconnectEventSource();
  };

  return {
    disconnect(): void {
      if (disconnected) {
        return;
      }
      disconnected = true;
      disconnectEventSource();
    },
  };
}

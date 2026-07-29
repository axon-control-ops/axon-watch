import { describe, expect, it, vi } from 'vitest';

import { startChatStreamSession } from './chat-stream-session';

type MessageHandler = ((event: MessageEvent) => void) | null;

function createEventSourceHarness() {
  let messageHandler: MessageHandler = null;
  let errorHandler: (() => void) | null = null;
  const instances: Array<{ close: ReturnType<typeof vi.fn> }> = [];
  const close = vi.fn();

  class MockEventSource {
    onmessage: MessageHandler = null;
    onerror: (() => void) | null = null;

    constructor(_url: string) {
      messageHandler = (event) => {
        this.onmessage?.(event);
      };
      errorHandler = () => {
        this.onerror?.();
      };
      instances.push({ close });
    }

    close(): void {
      close();
    }
  }

  return {
    EventSourceImpl: MockEventSource as unknown as typeof EventSource,
    close,
    instances,
    emit(payload: unknown): void {
      if (!messageHandler) {
        throw new Error('EventSource message handler was not attached');
      }
      messageHandler({ data: JSON.stringify(payload) } as MessageEvent);
    },
    triggerError(): void {
      errorHandler?.();
    },
  };
}

describe('startChatStreamSession', () => {
  it('delivers final content and disconnects after completion', () => {
    const harness = createEventSourceHarness();
    const onDelta = vi.fn();
    const onDone = vi.fn();

    startChatStreamSession({
      threadId: 'thread-1',
      messageId: 'message-1',
      onDelta,
      onDone,
      EventSourceImpl: harness.EventSourceImpl,
    });

    harness.emit({
      type: 'chat_stream_done',
      message_id: 'message-1',
      content: 'Finished response',
    });

    expect(onDelta).toHaveBeenCalledWith('Finished response');
    expect(onDone).toHaveBeenCalledTimes(1);
    expect(harness.close).toHaveBeenCalledTimes(1);
  });

  it('still disconnects when completion handling throws', () => {
    const harness = createEventSourceHarness();

    startChatStreamSession({
      threadId: 'thread-1',
      messageId: 'message-1',
      onDelta: vi.fn(),
      onDone: () => {
        throw new Error('completion handler failed');
      },
      EventSourceImpl: harness.EventSourceImpl,
    });

    expect(() =>
      harness.emit({
        type: 'chat_stream_done',
        message_id: 'message-1',
        content: 'Persisted response',
      }),
    ).toThrow('completion handler failed');
    expect(harness.close).toHaveBeenCalledTimes(1);
  });

  it('reconnects after a transient EventSource error instead of failing immediately', async () => {
    vi.useFakeTimers();
    const harness = createEventSourceHarness();
    const onError = vi.fn();
    const onDelta = vi.fn();

    startChatStreamSession({
      threadId: 'thread-1',
      messageId: 'message-1',
      onDelta,
      onError,
      EventSourceImpl: harness.EventSourceImpl,
      reconnectBaseMs: 10,
      maxReconnectAttempts: 3,
    });

    expect(harness.instances).toHaveLength(1);
    harness.triggerError();
    expect(onError).not.toHaveBeenCalled();

    await vi.advanceTimersByTimeAsync(10);
    expect(harness.instances.length).toBeGreaterThanOrEqual(2);

    harness.emit({
      type: 'chat_stream_delta',
      message_id: 'message-1',
      content: 'Recovered after drop',
    });
    expect(onDelta).toHaveBeenCalledWith('Recovered after drop');
    expect(onError).not.toHaveBeenCalled();
    vi.useRealTimers();
  });

  it('fails only after reconnect attempts are exhausted', async () => {
    vi.useFakeTimers();
    const harness = createEventSourceHarness();
    const onError = vi.fn();

    startChatStreamSession({
      threadId: 'thread-1',
      messageId: 'message-1',
      onDelta: vi.fn(),
      onError,
      EventSourceImpl: harness.EventSourceImpl,
      reconnectBaseMs: 5,
      maxReconnectAttempts: 2,
    });

    harness.triggerError();
    await vi.advanceTimersByTimeAsync(5);
    harness.triggerError();
    await vi.advanceTimersByTimeAsync(10);
    harness.triggerError();

    expect(onError).toHaveBeenCalledWith('chat stream disconnected', undefined);
    vi.useRealTimers();
  });

  it('settles when the hub closes without a matching done event', () => {
    const harness = createEventSourceHarness();
    const onError = vi.fn();
    const onDone = vi.fn();

    startChatStreamSession({
      threadId: 'thread-1',
      messageId: 'message-1',
      onDelta: vi.fn(),
      onDone,
      onError,
      EventSourceImpl: harness.EventSourceImpl,
    });

    harness.emit({ type: 'chat_stream_close' });

    expect(onDone).not.toHaveBeenCalled();
    expect(onError).toHaveBeenCalledWith('chat stream closed');
  });

  it('marks mid-run hub close as interrupted after deltas', () => {
    const harness = createEventSourceHarness();
    const onError = vi.fn();
    const onDone = vi.fn();
    const onDelta = vi.fn();

    startChatStreamSession({
      threadId: 'thread-1',
      messageId: 'message-1',
      onDelta,
      onDone,
      onError,
      EventSourceImpl: harness.EventSourceImpl,
    });

    harness.emit({
      type: 'chat_stream_delta',
      message_id: 'message-1',
      content: 'Working…',
    });
    harness.emit({ type: 'chat_stream_close' });

    expect(onDone).not.toHaveBeenCalled();
    expect(onDelta).toHaveBeenCalledWith('Working…');
    expect(onError).toHaveBeenCalledWith('chat stream interrupted');
  });

  it('does not double-settle when done is followed by close', () => {
    const harness = createEventSourceHarness();
    const onError = vi.fn();
    const onDone = vi.fn();

    startChatStreamSession({
      threadId: 'thread-1',
      messageId: 'message-1',
      onDelta: vi.fn(),
      onDone,
      onError,
      EventSourceImpl: harness.EventSourceImpl,
    });

    harness.emit({
      type: 'chat_stream_done',
      message_id: 'message-1',
      content: 'Done',
    });
    harness.emit({ type: 'chat_stream_close' });

    expect(onDone).toHaveBeenCalledTimes(1);
    expect(onError).not.toHaveBeenCalled();
  });
});

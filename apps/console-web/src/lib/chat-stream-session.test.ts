import { describe, expect, it, vi } from 'vitest';

import { startChatStreamSession } from './chat-stream-session';

type MessageHandler = ((event: MessageEvent) => void) | null;

function createEventSourceHarness() {
  let messageHandler: MessageHandler = null;
  const close = vi.fn();

  class MockEventSource {
    onmessage: MessageHandler = null;
    onerror: (() => void) | null = null;

    constructor(_url: string) {
      messageHandler = (event) => {
        this.onmessage?.(event);
      };
    }

    close(): void {
      close();
    }
  }

  return {
    EventSourceImpl: MockEventSource as unknown as typeof EventSource,
    close,
    emit(payload: unknown): void {
      if (!messageHandler) {
        throw new Error('EventSource message handler was not attached');
      }
      messageHandler({ data: JSON.stringify(payload) } as MessageEvent);
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
});

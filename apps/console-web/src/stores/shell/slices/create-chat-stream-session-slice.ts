import type { Ref } from 'vue';

import type { OperatorThreadEntry } from '../../../lib/operator-thread';

interface CreateChatStreamSessionSliceInput {
  activeIdeThreadId: Ref<string | null>;
  threadMessages: Ref<OperatorThreadEntry[]>;
  /** Message cache keyed by thread_id. */
  workspaceIdeThreadMessagesById: Ref<Record<string, OperatorThreadEntry[]>>;
  /** Live SSE sessions keyed by thread_id. */
  chatStreamSessionsByWorkspace: Map<string, { disconnect: () => void }>;
}

export function createChatStreamSessionSlice(input: CreateChatStreamSessionSliceInput) {
  function disconnectAllChatStreamSessions(): void {
    for (const session of input.chatStreamSessionsByWorkspace.values()) {
      session.disconnect();
    }
    input.chatStreamSessionsByWorkspace.clear();
  }

  /** Disconnect one thread's stream, or every stream when threadId is omitted. */
  function disconnectChatStreamSession(threadId?: string): void {
    if (threadId) {
      const session = input.chatStreamSessionsByWorkspace.get(threadId);
      if (session) {
        session.disconnect();
        input.chatStreamSessionsByWorkspace.delete(threadId);
      }
      return;
    }
    disconnectAllChatStreamSessions();
  }

  function patchThreadMessageContent(
    threadId: string,
    messageId: string,
    content: string,
    attachments?: OperatorThreadEntry['attachments'],
  ): void {
    const updateMessages = (messages: OperatorThreadEntry[]) =>
      messages.map((message) => {
        if (message.message_id !== messageId) {
          return message;
        }
        const next: OperatorThreadEntry = { ...message, content };
        if (attachments?.length) {
          next.attachments = attachments;
        }
        return next;
      });

    const cached = input.workspaceIdeThreadMessagesById.value[threadId];
    if (cached) {
      input.workspaceIdeThreadMessagesById.value = {
        ...input.workspaceIdeThreadMessagesById.value,
        [threadId]: updateMessages(cached),
      };
    }

    // Only paint into the visible transcript when this thread is focused.
    if (input.activeIdeThreadId.value === threadId) {
      input.threadMessages.value = updateMessages(input.threadMessages.value);
    }
  }

  return {
    disconnectChatStreamSession,
    disconnectAllChatStreamSessions,
    patchThreadMessageContent,
  };
}

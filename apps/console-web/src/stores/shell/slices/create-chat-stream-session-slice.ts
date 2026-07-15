import type { Ref } from 'vue';

import type { OperatorThreadEntry } from '../../../lib/operator-thread';
import type { WorkspaceRecord } from '../../../contracts/canonical';

interface CreateChatStreamSessionSliceInput {
  currentWorkspace: Ref<WorkspaceRecord | null>;
  threadMessages: Ref<OperatorThreadEntry[]>;
  workspaceIdeThreadMessagesById: Ref<Record<string, OperatorThreadEntry[]>>;
  chatStreamSessionsByWorkspace: Map<string, { disconnect: () => void }>;
}

export function createChatStreamSessionSlice(input: CreateChatStreamSessionSliceInput) {
  function disconnectAllChatStreamSessions(): void {
    for (const session of input.chatStreamSessionsByWorkspace.values()) {
      session.disconnect();
    }
    input.chatStreamSessionsByWorkspace.clear();
  }

  function disconnectChatStreamSession(workspaceId?: string): void {
    if (workspaceId) {
      const session = input.chatStreamSessionsByWorkspace.get(workspaceId);
      if (session) {
        session.disconnect();
        input.chatStreamSessionsByWorkspace.delete(workspaceId);
      }
      return;
    }
    disconnectAllChatStreamSessions();
  }

  function patchThreadMessageContent(
    workspaceId: string,
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

    if (input.currentWorkspace.value?.workspace_id === workspaceId) {
      input.threadMessages.value = updateMessages(input.threadMessages.value);
    }

    const cached = input.workspaceIdeThreadMessagesById.value[workspaceId];
    if (cached) {
      input.workspaceIdeThreadMessagesById.value = {
        ...input.workspaceIdeThreadMessagesById.value,
        [workspaceId]: updateMessages(cached),
      };
    }
  }

  return {
    disconnectChatStreamSession,
    disconnectAllChatStreamSessions,
    patchThreadMessageContent,
  };
}

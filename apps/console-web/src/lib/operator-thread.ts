import type { ThreadMessage } from '../contracts/canonical';

export type ThreadMessageRole = 'operator' | 'system' | 'agent';

export interface OperatorThreadEntry extends ThreadMessage {
  role: ThreadMessageRole;
  content: string;
  created_at: string;
}

export function createLocalThreadId(workspaceId: string): string {
  return `thread_local_${workspaceId}_${Date.now()}`;
}

export function buildOperatorThreadEntry(input: {
  threadId: string;
  content: string;
  workspaceId: string | null;
  runId: string | null;
  sequence: number;
  createdAt?: string;
}): OperatorThreadEntry {
  const createdAt = input.createdAt ?? new Date().toISOString();
  return {
    message_id: `message_operator_${input.sequence}_${Date.parse(createdAt)}`,
    thread_id: input.threadId,
    run_id: input.runId,
    workspace_id: input.workspaceId,
    role: 'operator',
    content: input.content.trim(),
    created_at: createdAt,
  };
}

export function buildSystemThreadReply(input: {
  threadId: string;
  workspaceId: string | null;
  runId: string | null;
  sequence: number;
  createdAt?: string;
}): OperatorThreadEntry {
  const createdAt = input.createdAt ?? new Date().toISOString();
  return {
    message_id: `message_system_${input.sequence}_${Date.parse(createdAt)}`,
    thread_id: input.threadId,
    run_id: input.runId,
    workspace_id: input.workspaceId,
    role: 'system',
    content: 'Command queued locally. Chat API wiring pending.',
    created_at: createdAt,
  };
}

export function appendOperatorCommand(input: {
  draft: string;
  threadId: string | null;
  workspaceId: string | null;
  runId: string | null;
  existingMessages: OperatorThreadEntry[];
}): {
  threadId: string;
  messages: OperatorThreadEntry[];
} {
  const content = input.draft.trim();
  const workspaceId = input.workspaceId;
  if (!content || !workspaceId) {
    return {
      threadId: input.threadId ?? '',
      messages: input.existingMessages,
    };
  }

  const threadId = input.threadId ?? createLocalThreadId(workspaceId);
  const sequence = input.existingMessages.length;
  const operatorEntry = buildOperatorThreadEntry({
    threadId,
    content,
    workspaceId,
    runId: input.runId,
    sequence,
  });
  const systemEntry = buildSystemThreadReply({
    threadId,
    workspaceId,
    runId: input.runId,
    sequence: sequence + 1,
    createdAt: operatorEntry.created_at,
  });

  return {
    threadId,
    messages: [...input.existingMessages, operatorEntry, systemEntry],
  };
}

export function mapChatMessageRecord(record: {
  message_id: string;
  thread_id: string;
  run_id: string | null;
  workspace_id: string | null;
  role: string;
  content: string;
  created_at: string;
}): OperatorThreadEntry {
  return {
    message_id: record.message_id,
    thread_id: record.thread_id,
    run_id: record.run_id,
    workspace_id: record.workspace_id,
    role:
      record.role === 'system'
        ? 'system'
        : record.role === 'agent'
          ? 'agent'
          : 'operator',
    content: record.content,
    created_at: record.created_at,
  };
}

export function mergeThreadMessages(
  existingMessages: OperatorThreadEntry[],
  incomingMessages: OperatorThreadEntry[],
): OperatorThreadEntry[] {
  const seen = new Set(existingMessages.map((message) => message.message_id));
  const appended = incomingMessages.filter((message) => !seen.has(message.message_id));
  return [...existingMessages, ...appended];
}

export function conversationEmptyStateLabel(messageCount: number): string {
  return messageCount > 0 ? 'Conversation active' : 'No active conversation';
}

export function canSubmitOperatorCommand(draft: string, workspaceId: string | null): boolean {
  return draft.trim().length > 0 && Boolean(workspaceId);
}

export function commandSeamHint(workspaceId: string | null): string {
  if (!workspaceId) {
    return 'Select a workspace to send operator commands.';
  }
  return 'Bounded operator commands only. Switch to IDE Agent dock for scoped plan/ask.';
}

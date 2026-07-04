import { describe, expect, it } from 'vitest';

import {
  appendOperatorCommand,
  buildOperatorThreadEntry,
  buildSystemThreadReply,
  canSubmitOperatorCommand,
  commandSeamHint,
  conversationEmptyStateLabel,
  createLocalThreadId,
  mapChatMessageRecord,
  mergeThreadMessages,
} from './operator-thread';

describe('operator-thread', () => {
  it('creates stable local thread ids from workspace scope', () => {
    expect(createLocalThreadId('workspace_alpha')).toMatch(/^thread_local_workspace_alpha_\d+$/);
  });

  it('builds operator and system thread entries', () => {
    const operatorEntry = buildOperatorThreadEntry({
      threadId: 'thread_local_test',
      content: '  inspect runtime  ',
      workspaceId: 'workspace_alpha',
      runId: 'run_test',
      sequence: 0,
      createdAt: '2026-07-04T10:00:00.000Z',
    });

    expect(operatorEntry).toMatchObject({
      thread_id: 'thread_local_test',
      workspace_id: 'workspace_alpha',
      run_id: 'run_test',
      role: 'operator',
      content: 'inspect runtime',
    });

    const systemEntry = buildSystemThreadReply({
      threadId: 'thread_local_test',
      workspaceId: 'workspace_alpha',
      runId: 'run_test',
      sequence: 1,
      createdAt: '2026-07-04T10:00:01.000Z',
    });

    expect(systemEntry.role).toBe('system');
    expect(systemEntry.content).toContain('Chat API wiring pending');
  });

  it('appends operator command pairs to the thread transcript', () => {
    const result = appendOperatorCommand({
      draft: 'start review',
      threadId: null,
      workspaceId: 'workspace_alpha',
      runId: null,
      existingMessages: [],
    });

    expect(result.threadId).toMatch(/^thread_local_workspace_alpha_/);
    expect(result.messages).toHaveLength(2);
    expect(result.messages[0]?.role).toBe('operator');
    expect(result.messages[1]?.role).toBe('system');
  });

  it('rejects empty drafts and missing workspace context', () => {
    expect(
      appendOperatorCommand({
        draft: '   ',
        threadId: 'thread_existing',
        workspaceId: 'workspace_alpha',
        runId: null,
        existingMessages: [],
      }).messages,
    ).toHaveLength(0);

    expect(
      appendOperatorCommand({
        draft: 'hello',
        threadId: null,
        workspaceId: null,
        runId: null,
        existingMessages: [],
      }).messages,
    ).toHaveLength(0);
  });

  it('derives seam labels and submit eligibility', () => {
    expect(conversationEmptyStateLabel(0)).toBe('No active conversation');
    expect(conversationEmptyStateLabel(2)).toBe('Conversation active');
    expect(canSubmitOperatorCommand('go', 'workspace_alpha')).toBe(true);
    expect(canSubmitOperatorCommand('go', null)).toBe(false);
    expect(commandSeamHint(null)).toContain('Select a workspace');
    expect(commandSeamHint('workspace_alpha')).toContain('active workspace');
  });

  it('maps API chat records and merges without duplicates', () => {
    const mapped = mapChatMessageRecord({
      message_id: 'message_operator_1',
      thread_id: 'thread_1',
      run_id: null,
      workspace_id: 'workspace_alpha',
      role: 'operator',
      content: 'hello',
      created_at: '2026-07-04T10:00:00.000Z',
    });
    expect(mapped.role).toBe('operator');

    const agentMapped = mapChatMessageRecord({
      message_id: 'message_agent_1',
      thread_id: 'thread_1',
      run_id: 'run_1',
      workspace_id: 'workspace_alpha',
      role: 'agent',
      content: 'Processing operator command.',
      created_at: '2026-07-04T10:00:02.000Z',
    });
    expect(agentMapped.role).toBe('agent');

    const merged = mergeThreadMessages(
      [mapped],
      [
        mapped,
        mapChatMessageRecord({
          message_id: 'message_system_1',
          thread_id: 'thread_1',
          run_id: null,
          workspace_id: 'workspace_alpha',
          role: 'system',
          content: 'ack',
          created_at: '2026-07-04T10:00:01.000Z',
        }),
      ],
    );
    expect(merged).toHaveLength(2);
  });
});

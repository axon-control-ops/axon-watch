import type { Ref } from 'vue';

import type { ComposerMode, RunRecord, ThreadMessage } from '../../contracts/canonical';
import { executeIdeRunRecovery } from '../../lib/ide-run-auto-recovery';
import { buildIdeComposerActivityLabel } from '../../lib/ide-composer-activity';
import { readIdeRunRecovery } from '../../lib/ide-run-recovery';

interface CreateIdeRunAutoRecoverySliceInput {
  autoRunRecoveryInFlight: { value: boolean };
  runs: Ref<RunRecord[]>;
  agentStreamActive: Ref<boolean>;
  commandMutationState: Ref<'idle' | 'submitting' | 'error'>;
  commandMutationError: Ref<string | null>;
  currentWorkspace: Ref<{ workspace_id: string } | null>;
  ideAgentRunId: Ref<string | null>;
  ideComposerActivity: Ref<{
    label: string;
    mode: ComposerMode;
    executionAccess: string;
    operatorPrompt: string;
  } | null>;
  agentExecutionAccess: Ref<string>;
  workspaceIdeThreadMessagesById: Ref<Record<string, ThreadMessage[]>>;
  activeThreadId: Ref<string | null>;
  loadRuns: (options?: { sync?: boolean }) => Promise<void>;
  setWorkspaceSurfaceThreadId: (
    workspaceId: string,
    surface: 'ide',
    threadId: string,
  ) => void;
  loadWorkspaceThread: (
    workspaceId: string,
    surface: 'ide',
    threadId: string,
  ) => Promise<void>;
  attachChatStream: (workspaceId: string, threadId: string, messageId: string) => void;
  dispatchIdeComposerMessage: (
    mode: ComposerMode,
    options?: {
      contentOverride?: string;
      linkedRunIdOverride?: string | null;
      threadIdOverride?: string;
      recoveryCountOverride?: number;
      clearDraftOnSuccess?: boolean;
    },
  ) => Promise<void>;
}

export function createIdeRunAutoRecoverySlice(input: CreateIdeRunAutoRecoverySliceInput) {
  async function autoContinueInterruptedIdeRun(): Promise<void> {
    const recovery = readIdeRunRecovery();
    if (!recovery || input.autoRunRecoveryInFlight.value) {
      return;
    }

    input.autoRunRecoveryInFlight.value = true;
    try {
      await executeIdeRunRecovery({
        recovery,
        loadRunPhase: async () => {
          await input.loadRuns({ sync: false });
          return input.runs.value.find((item) => item.run_id === recovery.runId)?.phase ?? null;
        },
        streamActive: () => input.agentStreamActive.value,
        mutationBusy: () => input.commandMutationState.value === 'submitting',
        currentWorkspaceId: () => input.currentWorkspace.value?.workspace_id ?? null,
        linkRun: (runId) => {
          input.ideAgentRunId.value = runId;
        },
        reportError: (message) => {
          input.commandMutationError.value = message;
        },
        reattach: async (record) => {
          input.ideAgentRunId.value = record.runId;
          input.setWorkspaceSurfaceThreadId(record.workspaceId, 'ide', record.threadId);
          input.activeThreadId.value = record.threadId;
          await input.loadWorkspaceThread(record.workspaceId, 'ide', record.threadId);
          input.ideAgentRunId.value = record.runId;
          const recoveredMessages =
            input.workspaceIdeThreadMessagesById.value[record.workspaceId] ?? [];
          const agentMessage = [...recoveredMessages]
            .reverse()
            .find(
              (message) =>
                message.role === 'agent' && message.run_id === record.runId,
            );
          if (agentMessage) {
            const operatorMessage = [...recoveredMessages]
              .reverse()
              .find(
                (message) =>
                  message.role === 'operator' && message.run_id === record.runId,
              );
            input.ideComposerActivity.value = {
              label: buildIdeComposerActivityLabel(
                record.mode,
                input.agentExecutionAccess.value,
              ),
              mode: record.mode,
              executionAccess: input.agentExecutionAccess.value,
              operatorPrompt: operatorMessage?.content ?? '',
            };
            input.attachChatStream(
              record.workspaceId,
              record.threadId,
              agentMessage.message_id,
            );
          }
        },
        dispatchContinuation: (continuation) =>
          input.dispatchIdeComposerMessage(continuation.mode, {
            contentOverride: continuation.content,
            linkedRunIdOverride: continuation.linkedRunId,
            threadIdOverride: continuation.threadId,
            recoveryCountOverride: continuation.recoveryCount,
            clearDraftOnSuccess: false,
          }),
      });
    } finally {
      input.autoRunRecoveryInFlight.value = false;
    }
  }

  return { autoContinueInterruptedIdeRun };
}

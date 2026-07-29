/** Shell slice: auto-open + live-follow continuous-worker specialist IDE streams. */

import { watch, type Ref } from 'vue';

import { fetchThreadHistory } from '../../../api/chat-api';
import type { WorkspaceChatThreadListItem } from '../../../api/chat-api';
import type { CompanyEmployeeRecord } from '../../../contracts/canonical';
import {
  buildIdeStreamActivityLabel,
  type IdeComposerActivity,
} from '../../../lib/agent-dock-activity-view';
import {
  decideBusyEmployeeStreamAttach,
  findIdeThreadIdForEmployee,
  listBusyEmployeeStreamTargets,
  resolveStreamingAgentMessageId,
} from '../../../lib/follow-busy-employee-ide-streams';
import { mapChatMessageRecord, type OperatorThreadEntry } from '../../../lib/operator-thread';
import { filterThreadMessagesForSurface } from '../../../lib/thread-surface-view';
import {
  defaultWorkspaceStreamUi,
  type WorkspaceStreamUiState,
} from '../../../lib/workspace-stream-ui';

export type AttachBusyEmployeeChatStream = (
  workspaceId: string,
  threadId: string,
  messageId: string,
  options?: {
    activity?: IdeComposerActivity | null;
    ideAgentRunId?: string | null;
    seedMessages?: OperatorThreadEntry[];
    preserveMessageCache?: boolean;
  },
) => void;

interface CreateBusyEmployeeIdeStreamSliceInput {
  currentWorkspaceId: Ref<string | null>;
  layoutMode: Ref<string>;
  companyEmployees: Ref<CompanyEmployeeRecord[]>;
  ideThreadsByWorkspaceId: Ref<Record<string, WorkspaceChatThreadListItem[]>>;
  workspaceIdeThreadMessagesById: Ref<Record<string, OperatorThreadEntry[]>>;
  loadIdeThreads: (workspaceId: string) => Promise<void>;
  ensureIdeThreadTabOpen: (threadId: string) => void;
  getWorkspaceStreamUi: (threadId: string) => WorkspaceStreamUiState;
  attachChatStream: AttachBusyEmployeeChatStream;
  /** True when an EventSource session is open for the thread. */
  hasLiveChatStreamSession?: (threadId: string) => boolean;
}

export function createBusyEmployeeIdeStreamSlice(input: CreateBusyEmployeeIdeStreamSliceInput) {
  let inFlight = false;

  async function followBusyEmployeeIdeStreams(): Promise<void> {
    const workspaceId = input.currentWorkspaceId.value?.trim() ?? '';
    if (!workspaceId || input.layoutMode.value !== 'ide' || inFlight) {
      return;
    }
    const targets = listBusyEmployeeStreamTargets(input.companyEmployees.value);
    if (!targets.length) {
      return;
    }

    inFlight = true;
    try {
      await input.loadIdeThreads(workspaceId);
      const threads = input.ideThreadsByWorkspaceId.value[workspaceId] ?? [];
      for (const target of targets) {
        const threadId = findIdeThreadIdForEmployee(threads, target.employeeId);
        if (threadId) {
          input.ensureIdeThreadTabOpen(threadId);
        }
        const streamUi = threadId
          ? input.getWorkspaceStreamUi(threadId)
          : defaultWorkspaceStreamUi();
        let messages = threadId
          ? (input.workspaceIdeThreadMessagesById.value[threadId] ?? [])
          : [];
        let messageId = resolveStreamingAgentMessageId(messages, target.runId);
        if (threadId && !messageId) {
          try {
            const history = await fetchThreadHistory(threadId);
            messages = filterThreadMessagesForSurface(
              history.items.map((item) => mapChatMessageRecord(item)),
              'ide',
            );
            input.workspaceIdeThreadMessagesById.value = {
              ...input.workspaceIdeThreadMessagesById.value,
              [threadId]: messages,
            };
            messageId = resolveStreamingAgentMessageId(messages, target.runId);
          } catch {
            continue;
          }
        }
        const decision = decideBusyEmployeeStreamAttach({
          threadId,
          resolvedMessageId: messageId,
          alreadyActive: Boolean(streamUi.active),
          alreadyMessageId: streamUi.messageId,
          hasLiveSession: Boolean(threadId && input.hasLiveChatStreamSession?.(threadId)),
        });
        if (decision !== 'attach' || !threadId || !messageId) {
          continue;
        }
        const operatorPrompt =
          [...messages]
            .reverse()
            .find(
              (message) =>
                message.role === 'operator' && (message.run_id ?? '').trim() === target.runId,
            )?.content ?? '';
        input.attachChatStream(workspaceId, threadId, messageId, {
          activity: {
            label: buildIdeStreamActivityLabel('full', 'agent'),
            mode: 'agent',
            executionAccess: 'full',
            operatorPrompt,
          },
          ideAgentRunId: target.runId,
          seedMessages: messages,
        });
      }
    } finally {
      inFlight = false;
    }
  }

  watch(
    [input.companyEmployees, input.layoutMode],
    () => {
      void followBusyEmployeeIdeStreams();
    },
    { flush: 'post' },
  );

  return { followBusyEmployeeIdeStreams };
}

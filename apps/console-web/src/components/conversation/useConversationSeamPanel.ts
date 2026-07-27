import { computed, ref, watch, type Ref } from 'vue';

import { applyChatUiAction, type ChatUiAction } from '../../lib/chat-ui-action';
import { agentContentLooksLikeErrorDump } from '../../lib/thread-message-view';
import {
  isMarkdownFileAgentResponse,
  shouldHideAgentReportInThread,
  shouldUseAgentMarkdownBlock,
} from '../../lib/agent-message-markdown';
import {
  prepareOperatorConversationDock,
  type ConversationDisplayItem,
} from '../../lib/operator-conversation-view';
import { conversationMessageWindow } from '../../lib/conversation-message-window';
import { operatorArtifactRecords } from '../../lib/operator-artifact-view';
import type { OperatorThreadEntry, ThreadMessageAttachment } from '../../lib/operator-thread';
import { agentContentHasTranscriptBlocks } from '../../lib/agent-transcript-blocks';
import { createTranscriptSegmentCache } from '../../lib/conversation-transcript-segment-cache';
import { sanitizeAgentThinkingForOperator, THINKING_SPEECH_FALLBACK } from '../../lib/agent-live-line-view';
import { prepareAgentTerminalOpen } from '../../lib/agent-terminal-open';
import {
  shouldShowAgentTerminalBackgroundControl,
  agentTerminalMirrorBadgeLabel,
} from '../../lib/agent-terminal-background-view';
import { armAgentShellMirror, agentShellMirrorActive } from '../../lib/agent-shell-mirror-state';
import { resolveChatAttachmentUrl } from '../../api/control-plane';
import { threadAttachmentUrlForImagePath } from '../../lib/thread-image-url';
import { isThreadImageAttachment } from '../../lib/thread-message-attachment-view';
import { useShellStore } from '../../stores/shell';

export function useConversationSeamPanel(rootRef: Ref<HTMLElement | null>, listRef: Ref<HTMLElement | null>, handleContentChange: () => void) {
  const shell = useShellStore();
  const conversationMessages = computed(() =>
    shell.layoutMode === 'ide' ? shell.threadMessages : shell.operatorThreadMessages,
  );
  const ideHistoryPage = ref(0);
  const ideMessageWindow = computed(() =>
    conversationMessageWindow(conversationMessages.value, ideHistoryPage.value),
  );
  const conversationDisplayItems = computed((): ConversationDisplayItem[] => {
    if (shell.layoutMode === 'ide') {
      return ideMessageWindow.value.items.map((message: OperatorThreadEntry) => ({
        kind: 'message' as const,
        message,
      }));
    }
    return prepareOperatorConversationDock(conversationMessages.value, {
      artifacts: operatorArtifactRecords.value,
    }).items;
  });

  const conversationDockHint = computed(() =>
    shell.layoutMode === 'operator'
      ? 'Actions, KAIRO turns, and receipts — not the run queue. Open loops live in the KAIRO briefing below.'
      : null,
  );
  const showAgentWorking = computed(
    () =>
      shell.agentStreamActive ||
      (shell.layoutMode === 'ide' && Boolean(shell.ideComposerActivity)),
  );
  const agentWorkingLabel = computed(() => {
    if (shell.agentStreamActive && shell.agentStreamMessageId) {
      return (
        shell.ideComposerActivity?.label ??
        'Agent — streaming runtime output…'
      );
    }
    if (shell.agentStreamActive) {
      return THINKING_SPEECH_FALLBACK;
    }
    return shell.ideComposerActivity?.label ?? 'Agent is working…';
  });

  const expandedErrorByMessageId = ref<Record<string, boolean>>({});
  const expandedSystemByMessageId = ref<Record<string, boolean>>({});
  const expandedThinkingKeys = ref<Record<string, boolean>>({});
  const { transcriptSegments } = createTranscriptSegmentCache();

  function toggleErrorExpanded(messageId: string): void {
    expandedErrorByMessageId.value = {
      ...expandedErrorByMessageId.value,
      [messageId]: !expandedErrorByMessageId.value[messageId],
    };
  }

  function isMarkdownBlock(content: string, isComplete = true): boolean {
    return shouldUseAgentMarkdownBlock(content, isComplete) && !isErrorDump(content);
  }

  function isMarkdownFileBlock(content: string): boolean {
    return isMarkdownFileAgentResponse(content);
  }

  function shouldShowEditorStub(messageId: string, content: string): boolean {
    return Boolean(shell.agentReportEditorLink(messageId)) && shouldHideAgentReportInThread(content);
  }

  function isErrorDump(content: string): boolean {
    return agentContentLooksLikeErrorDump(content);
  }

  function isErrorExpanded(messageId: string): boolean {
    return Boolean(expandedErrorByMessageId.value[messageId]);
  }

  function toggleSystemExpanded(messageId: string): void {
    expandedSystemByMessageId.value = {
      ...expandedSystemByMessageId.value,
      [messageId]: !expandedSystemByMessageId.value[messageId],
    };
  }

  function isSystemExpanded(messageId: string): boolean {
    return Boolean(expandedSystemByMessageId.value[messageId]);
  }

  function isStreamingMessage(messageId: string): boolean {
    return shell.agentStreamActive && shell.agentStreamMessageId === messageId;
  }

  function hasTranscriptBlocks(content: string): boolean {
    return agentContentHasTranscriptBlocks(content);
  }

  function segmentKey(messageId: string, index: number): string {
    return `${messageId}:${index}`;
  }

  function revealTerminalPanel(segment: { command: string; output: string; open: boolean }): void {
    prepareAgentTerminalOpen(segment);
    void shell.backgroundIdeAgentRun();
  }

  function backgroundAgentTerminalRun(segment?: {
    command: string;
    output: string;
    open: boolean;
  }): void {
    if (segment) {
      prepareAgentTerminalOpen(segment);
    } else {
      armAgentShellMirror();
    }
    void shell.backgroundIdeAgentRun();
  }

  async function continueTerminalInBackground(command: string): Promise<void> {
    await shell.runCommandInAgentBackgroundTerminal(command);
  }

  function showTerminalBackgroundControl(messageId: string, segmentOpen: boolean): boolean {
    return shouldShowAgentTerminalBackgroundControl({
      canStopIdeAgentRun: shell.canStopIdeAgentRun,
      terminalBlockRunning: segmentOpen && isStreamingMessage(messageId),
    });
  }

  function terminalMirrorBadge(segmentOpen: boolean): string | null {
    return agentTerminalMirrorBadgeLabel({
      segmentOpen,
      mirrorActive: agentShellMirrorActive.value,
    });
  }

  function thinkingBodyText(text: string): string {
    return sanitizeAgentThinkingForOperator(text) || THINKING_SPEECH_FALLBACK;
  }

  async function copyTerminalOutput(output: string): Promise<void> {
    if (typeof navigator === 'undefined' || !navigator.clipboard || !output.trim()) {
      return;
    }
    await navigator.clipboard.writeText(output);
  }

  function isThinkingExpanded(key: string, open: boolean): boolean {
    return expandedThinkingKeys.value[key] ?? open;
  }

  function toggleThinking(key: string, open: boolean): void {
    expandedThinkingKeys.value = {
      ...expandedThinkingKeys.value,
      [key]: !isThinkingExpanded(key, open),
    };
  }

  function displayItemKey(item: ConversationDisplayItem): string {
    if (item.kind === 'command_turn' || item.kind === 'dock_banner' || item.kind === 'artifact') {
      return item.messageId;
    }
    return item.message.message_id;
  }

  function attachmentUrlForImagePath(message: OperatorThreadEntry, path: string): string | null {
    return threadAttachmentUrlForImagePath(path, message.attachments ?? []);
  }

  function applyArtifactAction(action: { uiAction: ChatUiAction | null }): void {
    if (!action.uiAction) {
      return;
    }
    applyChatUiAction(shell as unknown as Parameters<typeof applyChatUiAction>[0], action.uiAction);
  }

  function messageAttachments(message: OperatorThreadEntry): ThreadMessageAttachment[] {
    return message.attachments ?? [];
  }

  interface EnlargedAttachmentPreview {
    url: string;
    filename: string;
  }

  const enlargedAttachment = ref<EnlargedAttachmentPreview | null>(null);

  function openAttachmentPreview(attachment: ThreadMessageAttachment): void {
    const url = resolveChatAttachmentUrl(attachment.url);
    if (!isThreadImageAttachment(attachment)) {
      if (typeof window !== 'undefined') {
        window.open(url, '_blank', 'noopener,noreferrer');
      }
      return;
    }
    enlargedAttachment.value = {
      url,
      filename: attachment.filename,
    };
  }

  function closeAttachmentLightbox(): void {
    enlargedAttachment.value = null;
  }

  function compactCommandSummary(output: string): string {
    const line = output.split('\n').map((part) => part.trim()).find(Boolean);
    if (!line) {
      return 'No output';
    }
    return line.length <= 96 ? line : `${line.slice(0, 93)}…`;
  }

  function isEmptyStreamingAgent(message: { role: string; message_id: string; content: string }): boolean {
    return message.role === 'agent' && !message.content.trim() && isStreamingMessage(message.message_id);
  }

  function showEarlierMessages(): void {
    if (ideMessageWindow.value.olderCount > 0) {
      ideHistoryPage.value += 1;
    }
  }

  function showNewerMessages(): void {
    ideHistoryPage.value = Math.max(0, ideHistoryPage.value - 1);
  }

  function showLatestMessages(): void {
    ideHistoryPage.value = 0;
  }

  watch(
    () => shell.activeIdeThreadId,
    () => {
      ideHistoryPage.value = 0;
    },
  );

  const conversationContentRevision = computed(() => {
    const items = conversationDisplayItems.value;
    const last = items.at(-1);
    if (!last) {
      return 'empty';
    }
    if (last.kind === 'message') {
      return `${items.length}:${last.message.message_id}:${last.message.content.length}`;
    }
    if (last.kind === 'command_turn') {
      return `${items.length}:${last.messageId}:${last.execution.output.length}`;
    }
    if (last.kind === 'artifact') {
      return `${items.length}:${last.messageId}:${last.artifact.body.length}`;
    }
    return `${items.length}:${last.messageId}:${last.text.length}`;
  });

  watch(
    conversationContentRevision,
    () => {
      handleContentChange();
    },
    { immediate: true },
  );

  return {
    shell,
    conversationDisplayItems,
    ideMessageWindow,
    conversationDockHint,
    showAgentWorking,
    agentWorkingLabel,
    toggleErrorExpanded,
    isMarkdownBlock,
    isMarkdownFileBlock,
    shouldShowEditorStub,
    isErrorDump,
    isErrorExpanded,
    toggleSystemExpanded,
    isSystemExpanded,
    isStreamingMessage,
    hasTranscriptBlocks,
    segmentKey,
    revealTerminalPanel,
    backgroundAgentTerminalRun,
    continueTerminalInBackground,
    showTerminalBackgroundControl,
    terminalMirrorBadge,
    thinkingBodyText,
    copyTerminalOutput,
    isThinkingExpanded,
    toggleThinking,
    displayItemKey,
    attachmentUrlForImagePath,
    applyArtifactAction,
    messageAttachments,
    enlargedAttachment,
    openAttachmentPreview,
    closeAttachmentLightbox,
    compactCommandSummary,
    isEmptyStreamingAgent,
    showEarlierMessages,
    showNewerMessages,
    showLatestMessages,
    transcriptSegments,
    rootRef,
    listRef,
  };
}

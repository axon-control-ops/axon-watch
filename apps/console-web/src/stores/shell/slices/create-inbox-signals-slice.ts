import type { Ref } from 'vue';

import { acknowledgeInboxSignals, fetchInbox } from '../../../api/inbox-api';
import type { InboxItem, OperatorBriefing, SignalView } from '../../../contracts/canonical';
import {
  canVerifyDismissHandoffSignal,
  writePendingHandoffDismissSignalId,
} from '../../../lib/signal-handoff-dismiss';
import type { InboxLoadState } from '../types';

interface CreateInboxSignalsSliceInput {
  inboxItems: Ref<InboxItem[]>;
  signalViews: Ref<SignalView[]>;
  inboxLoadState: Ref<InboxLoadState>;
  inboxError: Ref<string | null>;
  signalClearState: Ref<'idle' | 'clearing'>;
  signalClearError: Ref<string | null>;
  highlightedSignalId: Ref<string | null>;
  pendingHandoffDismissSignalId: Ref<string | null>;
  operatorBriefing: Ref<OperatorBriefing | null>;
  loadOperatorBriefing: () => Promise<void>;
  loadRuntimeSummary: () => Promise<void>;
}

export function createInboxSignalsSlice(input: CreateInboxSignalsSliceInput) {
  async function loadInbox(): Promise<void> {
    input.inboxLoadState.value = 'loading';
    input.inboxError.value = null;

    try {
      const inbox = await fetchInbox();
      input.inboxItems.value = inbox.items;
      input.signalViews.value = inbox.items;
      input.inboxLoadState.value = 'loaded';
    } catch (error) {
      input.inboxLoadState.value = 'error';
      input.inboxError.value = error instanceof Error ? error.message : 'inbox request failed';
    }
  }

  async function dismissInboxSignalIds(signalIds: string[]): Promise<void> {
    const normalized = [...new Set(signalIds.map((id) => id.trim()).filter(Boolean))];
    if (!normalized.length) {
      return;
    }

    await acknowledgeInboxSignals(normalized);
    await Promise.all([loadInbox(), input.loadOperatorBriefing(), input.loadRuntimeSummary()]);
  }

  async function verifyAndDismissHandoffSignal(signalId: string): Promise<void> {
    input.signalClearError.value = null;
    await loadInbox();
    const gate = canVerifyDismissHandoffSignal(
      signalId,
      input.inboxItems.value.map((item) => ({ signal_id: item.signal_id })),
    );
    if (!gate.allowed) {
      input.signalClearError.value = gate.reason ?? 'Signal cannot be dismissed yet.';
      return;
    }

    input.signalClearState.value = 'clearing';
    try {
      await dismissInboxSignalIds([signalId]);
      if (input.pendingHandoffDismissSignalId.value === signalId) {
        input.pendingHandoffDismissSignalId.value = null;
        writePendingHandoffDismissSignalId(null);
      }
      input.highlightedSignalId.value = null;
    } catch (error) {
      input.signalClearError.value =
        error instanceof Error ? error.message : 'verify and dismiss request failed';
    } finally {
      input.signalClearState.value = 'idle';
    }
  }

  async function dismissLinkedHandoffSignalAfterRunComplete(): Promise<void> {
    const signalId = input.pendingHandoffDismissSignalId.value?.trim();
    if (!signalId) {
      return;
    }

    try {
      await dismissInboxSignalIds([signalId]);
    } catch {
      // Run completion should still succeed even if watch ack is temporarily unavailable.
    } finally {
      input.pendingHandoffDismissSignalId.value = null;
      writePendingHandoffDismissSignalId(null);
    }
  }

  async function clearActiveSignals(): Promise<void> {
    const signalIds =
      input.operatorBriefing.value?.top_signals.map((signal) => signal.signal_id) ??
      input.signalViews.value.map((signal) => signal.signal_id);
    if (!signalIds.length || input.signalClearState.value === 'clearing') {
      return;
    }

    input.signalClearState.value = 'clearing';
    input.signalClearError.value = null;
    input.highlightedSignalId.value = null;

    try {
      await dismissInboxSignalIds(signalIds);
    } catch (error) {
      input.signalClearError.value =
        error instanceof Error ? error.message : 'clear signals request failed';
    } finally {
      input.signalClearState.value = 'idle';
    }
  }

  return {
    loadInbox,
    dismissInboxSignalIds,
    verifyAndDismissHandoffSignal,
    dismissLinkedHandoffSignalAfterRunComplete,
    clearActiveSignals,
  };
}

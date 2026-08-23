import { onScopeDispose, type Ref } from 'vue';

import { acknowledgeInboxSignals, fetchInbox } from '../../../api/inbox-api';
import type { InboxItem, OperatorBriefing, SignalView } from '../../../contracts/canonical';
import { filterActionableOpenSignals } from '../../../lib/operator-signal-count';
import {
  canVerifyDismissHandoffSignal,
  writePendingHandoffDismissSignalId,
} from '../../../lib/signal-handoff-dismiss';
import { COMPANY_REFRESH_MS } from '../../../lib/ui-refresh-guardrails';
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
  loadRuntimeSummary: (options?: { background?: boolean }) => Promise<void>;
}

export function createInboxSignalsSlice(input: CreateInboxSignalsSliceInput) {
  let inflightInbox: Promise<void> | null = null;
  let inflightForceInbox: Promise<void> | null = null;
  let refreshTimer: ReturnType<typeof setInterval> | null = null;

  async function loadInbox(options?: { background?: boolean; force?: boolean }): Promise<void> {
    const hasCached = input.inboxLoadState.value === 'loaded';
    const background = options?.background === true || hasCached;
    const force = options?.force === true;

    // A forced refresh (operator clicked "Refresh") must reach real IMAP, so
    // it gets its own single-flight lane rather than joining/being skipped by
    // whatever passive background poll happens to be in flight already.
    if (force) {
      if (inflightForceInbox) {
        return inflightForceInbox;
      }
    } else if (inflightInbox) {
      return inflightInbox;
    }

    if (!background) {
      input.inboxLoadState.value = 'loading';
      input.inboxError.value = null;
    }

    const request = (async () => {
      try {
        const inbox = await fetchInbox({ force });
        input.inboxItems.value = inbox.items;
        input.signalViews.value = inbox.items;
        input.inboxLoadState.value = 'loaded';
        input.inboxError.value = null;
      } catch (error) {
        if (!hasCached) {
          input.inboxLoadState.value = 'error';
          input.inboxError.value = error instanceof Error ? error.message : 'inbox request failed';
        }
      } finally {
        if (force) {
          inflightForceInbox = null;
        } else {
          inflightInbox = null;
        }
      }
    })();

    if (force) {
      inflightForceInbox = request;
    } else {
      inflightInbox = request;
    }
    return request;
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
    const fromInbox = filterActionableOpenSignals(input.inboxItems.value).map(
      (signal) => signal.signal_id,
    );
    const signalIds = fromInbox.length
      ? fromInbox
      : (input.operatorBriefing.value?.top_signals.map((signal) => signal.signal_id) ??
        input.signalViews.value.map((signal) => signal.signal_id));
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

  // Fleet-wide, not workspace-scoped, so it just runs for the store's whole
  // lifetime rather than watching a workspace switch. Without this, a tab
  // left open shows whatever inbox snapshot loaded at mount forever -- stale
  // suggested-reply text and stale "unread" counts included -- until the
  // operator happens to hit the manual Refresh button or reload the page.
  refreshTimer = setInterval(() => {
    void loadInbox({ background: true });
  }, COMPANY_REFRESH_MS);
  onScopeDispose(() => {
    if (refreshTimer !== null) {
      clearInterval(refreshTimer);
      refreshTimer = null;
    }
  });

  return {
    loadInbox,
    dismissInboxSignalIds,
    verifyAndDismissHandoffSignal,
    dismissLinkedHandoffSignalAfterRunComplete,
    clearActiveSignals,
  };
}

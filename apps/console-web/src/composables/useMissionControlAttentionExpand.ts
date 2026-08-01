import { ref, watch, type Ref } from 'vue';

type AttentionSignal = {
  signal_id: string;
  severity?: string | null;
};

type AttentionExpandShell = {
  layoutMode: string;
  highlightedSignalId: string | null;
  attentionSignals: AttentionSignal[];
  toggleSignalDetails: (signalId: string) => void;
};

/** Keep the top Mission Control Attention card expanded for the current workspace. */
export function useMissionControlAttentionExpand(shell: AttentionExpandShell): {
  attentionAutoExpanded: Ref<boolean>;
} {
  const attentionAutoExpanded = ref(false);

  watch(
    () =>
      [
        shell.layoutMode,
        shell.highlightedSignalId,
        shell.attentionSignals.map((signal) => signal.signal_id).join('|'),
      ] as const,
    () => {
      if (shell.layoutMode !== 'operator') {
        return;
      }
      const signals = shell.attentionSignals;
      if (!signals.length) {
        return;
      }
      const highlightedInList = signals.some(
        (signal) => signal.signal_id === shell.highlightedSignalId,
      );
      if (highlightedInList) {
        attentionAutoExpanded.value = true;
        return;
      }
      const primary =
        signals.find((signal) => signal.severity === 'critical') ??
        signals.find((signal) => signal.severity === 'high') ??
        signals[0];
      if (!primary?.signal_id) {
        return;
      }
      shell.toggleSignalDetails(primary.signal_id);
      attentionAutoExpanded.value = true;
      // #region agent log
      fetch('http://127.0.0.1:7706/ingest/90bcaec2-2b39-4d4a-84b5-157c12735440', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Debug-Session-Id': 'db8bb4',
        },
        body: JSON.stringify({
          sessionId: 'db8bb4',
          runId: 'tx-needs-you',
          hypothesisId: 'A5',
          location: 'useMissionControlAttentionExpand.ts:auto-expand',
          message: 'Auto-expanded top Attention signal',
          data: {
            signalId: primary.signal_id,
            severity: primary.severity,
            attentionCount: signals.length,
            priorHighlighted: shell.highlightedSignalId,
          },
          timestamp: Date.now(),
        }),
      }).catch(() => {});
      // #endregion
    },
    { immediate: true },
  );

  return { attentionAutoExpanded };
}

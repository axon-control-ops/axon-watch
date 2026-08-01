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
    },
    { immediate: true },
  );

  return { attentionAutoExpanded };
}

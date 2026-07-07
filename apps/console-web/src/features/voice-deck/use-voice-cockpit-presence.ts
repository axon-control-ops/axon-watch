import { onUnmounted, watch } from 'vue';

import {
  shouldReactToBriefingSpokenAlert,
  spokenAlertSignature,
} from './voice-cockpit-presence';
import { useShellStore } from '../../stores/shell';

let lastDeliveredSignature = '';

export function resetVoiceCockpitDeliveryState(): void {
  lastDeliveredSignature = '';
}

export function useVoiceCockpitPresence(): void {
  const shell = useShellStore();

  const stop = watch(
    () => shell.operatorBriefing?.operator_presence?.spoken_alert,
    (alert) => {
      if (!shouldReactToBriefingSpokenAlert(alert)) {
        return;
      }
      const signature = spokenAlertSignature(alert);
      if (signature === lastDeliveredSignature) {
        return;
      }
      lastDeliveredSignature = signature;
      void shell.deliverKairoSpokenAlert(alert);
    },
    { deep: true, immediate: true },
  );

  onUnmounted(() => {
    stop();
  });
}

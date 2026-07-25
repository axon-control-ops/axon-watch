import { onUnmounted } from 'vue';

import { registerVoiceDeckSpokenAlertHandler } from '../../lib/spoken-alert-delivery';

import { registerVoiceDeckOnBoot } from './voice-deck';

export function useVoiceDeckOnBoot(): void {
  registerVoiceDeckOnBoot();

  onUnmounted(() => {
    registerVoiceDeckSpokenAlertHandler(null);
  });
}

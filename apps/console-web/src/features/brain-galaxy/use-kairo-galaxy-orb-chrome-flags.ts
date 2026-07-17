import { computed } from 'vue';

import { kairoConversationPhase } from '../kairo-conversation/kairo-conversation-state';

export function useKairoGalaxyOrbChromeFlags(input: {
  shell: { kairoSpeechActive: boolean; layoutMode: string };
  placementMode: 'viewport' | 'embedded';
}) {
  const showInterrupt = computed(
    () => input.shell.kairoSpeechActive || kairoConversationPhase.value === 'thinking',
  );
  const showIdeClose = computed(
    () => input.placementMode === 'viewport' && input.shell.layoutMode === 'ide',
  );

  return { showInterrupt, showIdeClose };
}

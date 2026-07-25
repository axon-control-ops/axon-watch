import { ref } from 'vue';

export interface BrainGalaxyConversationFocus {
  nodeId: string;
  workspaceId: string | null;
  signalId: string | null;
  label: string;
}

export const brainGalaxyConversationFocus = ref<BrainGalaxyConversationFocus | null>(null);

export function setBrainGalaxyConversationFocus(focus: BrainGalaxyConversationFocus | null): void {
  brainGalaxyConversationFocus.value = focus;
}

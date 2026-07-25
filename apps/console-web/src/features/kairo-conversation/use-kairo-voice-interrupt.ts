import { onBeforeUnmount } from 'vue';

import { clearKairoVoiceFollowupWindow } from '../../lib/kairo-voice-followup-window';
import { useShellStore } from '../../stores/shell';
import { setKairoConversationPhase } from './kairo-conversation-state';
import { registerKairoVoiceInterruptHandler } from './kairo-shared-speech-capture';

export function useKairoVoiceInterrupt(): void {
  const shell = useShellStore();

  const unregister = registerKairoVoiceInterruptHandler(() => {
    shell.interruptKairoVoice();
    clearKairoVoiceFollowupWindow();
    setKairoConversationPhase('idle');
  });

  onBeforeUnmount(() => {
    unregister();
  });
}

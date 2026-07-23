import { onBeforeUnmount } from 'vue';

import { duckKairoPlaybackGain, restoreKairoPlaybackGain } from '../../lib/kairo-playback-control';
import { bargeInDuckGain } from './kairo-duplex-phase';
import { clearKairoVoiceFollowupWindow } from '../../lib/kairo-voice-followup-window';
import { useShellStore } from '../../stores/shell';
import { setKairoConversationPhase } from './kairo-conversation-state';
import { registerKairoVoiceInterruptHandler } from './kairo-shared-speech-capture';

export function useKairoVoiceInterrupt(): void {
  const shell = useShellStore();

  const unregister = registerKairoVoiceInterruptHandler(() => {
    duckKairoPlaybackGain(bargeInDuckGain(true));
    shell.interruptKairoVoice();
    restoreKairoPlaybackGain();
    clearKairoVoiceFollowupWindow();
    setKairoConversationPhase('idle');
  });

  onBeforeUnmount(() => {
    unregister();
  });
}

import { clearKairoVoiceFollowupWindow } from '../../lib/kairo-voice-followup-window';
import { setKairoConversationPhase } from '../kairo-conversation/kairo-conversation-state';

export type KairoGalaxyOrbInterruptShell = {
  interruptKairoVoice: () => void;
};

export function handleKairoGalaxyOrbInterrupt(shell: KairoGalaxyOrbInterruptShell): void {
  shell.interruptKairoVoice();
  clearKairoVoiceFollowupWindow();
  setKairoConversationPhase('idle');
}

import { onBeforeUnmount, ref } from 'vue';

import { isSpeechCaptureSupported, SpeechCaptureSession } from './speech-capture';
import { setKairoConversationPhase } from './kairo-conversation-state';

export function useKairoSpeechCapture(options: {
  privacyBlocked: () => boolean;
  onFinalTranscript: (transcript: string) => Promise<void>;
}) {
  const session = new SpeechCaptureSession();
  const supported = isSpeechCaptureSupported();
  const capturing = ref(false);
  const interimTranscript = ref('');

  function canCapture(): boolean {
    return supported && !options.privacyBlocked() && !capturing.value;
  }

  function startCapture(): boolean {
    if (!canCapture()) {
      return false;
    }
    capturing.value = true;
    interimTranscript.value = '';
    setKairoConversationPhase('listening');
    return session.start({
      onInterim: (transcript) => {
        interimTranscript.value = transcript;
      },
      onFinal: (transcript) => {
        interimTranscript.value = '';
        capturing.value = false;
        void options.onFinalTranscript(transcript);
      },
      onError: () => {
        capturing.value = false;
        interimTranscript.value = '';
        setKairoConversationPhase('idle');
      },
      onEnd: () => {
        capturing.value = false;
        if (interimTranscript.value) {
          void options.onFinalTranscript(interimTranscript.value);
          interimTranscript.value = '';
        }
      },
    });
  }

  function stopCapture(): void {
    session.stop();
  }

  onBeforeUnmount(() => {
    session.stop();
  });

  return {
    supported,
    capturing,
    interimTranscript,
    canCapture,
    startCapture,
    stopCapture,
  };
}

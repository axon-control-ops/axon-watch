import { onBeforeUnmount, onMounted } from 'vue';

import { useShellStore } from '../stores/shell';

export function useIdeKairoInterrupt(): void {
  const shell = useShellStore();

  function handleKeydown(event: KeyboardEvent): void {
    if (shell.layoutMode !== 'ide' || event.key !== 'Escape') {
      return;
    }
    if (!shell.kairoSpeechActive) {
      return;
    }
    event.preventDefault();
    shell.interruptKairoVoice();
  }

  onMounted(() => {
    window.addEventListener('keydown', handleKeydown);
  });

  onBeforeUnmount(() => {
    window.removeEventListener('keydown', handleKeydown);
  });
}

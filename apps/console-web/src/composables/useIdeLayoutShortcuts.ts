import { onMounted, onUnmounted } from 'vue';

import { useShellStore } from '../stores/shell';

function isEditableTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) {
    return false;
  }

  const tag = target.tagName;
  return (
    tag === 'INPUT' ||
    tag === 'TEXTAREA' ||
    target.isContentEditable ||
    Boolean(target.closest('.command-seam__input, .xterm-helper-textarea'))
  );
}

export function useIdeLayoutShortcuts(): void {
  const shell = useShellStore();

  function onKeyDown(event: KeyboardEvent): void {
    if (shell.layoutMode !== 'ide' || isEditableTarget(event.target)) {
      return;
    }

    const mod = event.metaKey || event.ctrlKey;
    if (!mod) {
      return;
    }

    if (event.key.toLowerCase() === 'b') {
      event.preventDefault();
      shell.toggleIdeExplorer();
      return;
    }

    if (event.key === '\\') {
      event.preventDefault();
      shell.toggleAgentDock();
    }
  }

  onMounted(() => {
    window.addEventListener('keydown', onKeyDown);
  });

  onUnmounted(() => {
    window.removeEventListener('keydown', onKeyDown);
  });
}

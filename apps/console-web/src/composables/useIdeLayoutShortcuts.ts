import { onMounted, onUnmounted } from 'vue';

import { resolveIdeLayoutShortcut } from '../lib/ide-layout-shortcuts';
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
    const action = resolveIdeLayoutShortcut({
      layoutMode: shell.layoutMode,
      modKey: event.metaKey || event.ctrlKey,
      key: event.key,
      editableTarget: isEditableTarget(event.target),
    });

    if (!action) {
      return;
    }

    event.preventDefault();

    if (action === 'toggle-explorer') {
      shell.toggleIdeExplorer();
      return;
    }

    if (action === 'toggle-agent-dock') {
      shell.toggleAgentDock();
      return;
    }

    shell.toggleIdeTerminalPanel();
  }

  onMounted(() => {
    window.addEventListener('keydown', onKeyDown);
  });

  onUnmounted(() => {
    window.removeEventListener('keydown', onKeyDown);
  });
}

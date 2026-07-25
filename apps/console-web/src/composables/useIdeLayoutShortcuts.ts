import { onMounted, onUnmounted } from 'vue';

import { resolveIdeLayoutShortcut } from '../lib/ide-layout-shortcuts';
import { handleIdeLayoutShortcutAction } from './useIdeEditorStatusBar';
import { useShellStore } from '../stores/shell';

function isFormOrTerminalEditable(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) {
    return false;
  }

  const tag = target.tagName;
  return (
    tag === 'INPUT' ||
    tag === 'TEXTAREA' ||
    Boolean(target.closest('.command-seam__input, .xterm-helper-textarea, .xterm'))
  );
}

function isEditableTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) {
    return false;
  }

  return (
    isFormOrTerminalEditable(target) ||
    target.isContentEditable ||
    Boolean(target.closest('[contenteditable="true"]'))
  );
}

export function useIdeLayoutShortcuts(): void {
  const shell = useShellStore();

  function onKeyDown(event: KeyboardEvent): void {
    const action = resolveIdeLayoutShortcut({
      layoutMode: shell.layoutMode,
      modKey: event.metaKey || event.ctrlKey,
      shiftKey: event.shiftKey,
      key: event.key,
      formOrTerminalEditable: isFormOrTerminalEditable(event.target),
      editableTarget: isEditableTarget(event.target),
    });

    if (!action) {
      return;
    }

    event.preventDefault();
    event.stopPropagation();
    handleIdeLayoutShortcutAction(action, shell);
  }

  onMounted(() => {
    // Capture so Mod+J wins over TipTap/AI bubble menus in the editor.
    window.addEventListener('keydown', onKeyDown, true);
  });

  onUnmounted(() => {
    window.removeEventListener('keydown', onKeyDown, true);
  });
}

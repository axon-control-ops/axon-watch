import { onBeforeUnmount, ref } from 'vue';

import {
  dispatchOrbRadialMenuAction,
  type OrbRadialMenuAction,
} from './galaxy-orb-radial-menu';
import type { useShellStore } from '../../stores/shell';

type ShellStore = ReturnType<typeof useShellStore>;

export function useGalaxyOrbRadialMenu(input: {
  shell: ShellStore;
  onTalk: () => void | Promise<void>;
}) {
  const open = ref(false);
  let dismissListener: ((event: PointerEvent) => void) | null = null;

  function removeDismissListener(): void {
    if (!dismissListener) {
      return;
    }
    document.removeEventListener('pointerdown', dismissListener, { capture: true });
    dismissListener = null;
  }

  function closeMenu(): void {
    open.value = false;
    removeDismissListener();
  }

  function attachDismissListener(): void {
    removeDismissListener();
    dismissListener = (event: PointerEvent) => {
      const target = event.target;
      if (!(target instanceof Element)) {
        return;
      }
      if (target.closest('.kairo-galaxy-orb-radial-menu, .kairo-galaxy-orb__trigger')) {
        return;
      }
      closeMenu();
    };
    window.setTimeout(() => {
      if (dismissListener) {
        document.addEventListener('pointerdown', dismissListener, { capture: true });
      }
    }, 0);
  }

  function toggleMenu(): void {
    if (open.value) {
      closeMenu();
      return;
    }
    open.value = true;
    attachDismissListener();
  }

  function dispatchAction(action: OrbRadialMenuAction): void {
    closeMenu();
    dispatchOrbRadialMenuAction(action, input.shell, input.onTalk);
  }

  onBeforeUnmount(() => {
    removeDismissListener();
  });

  return {
    open,
    toggleMenu,
    closeMenu,
    dispatchAction,
  };
}

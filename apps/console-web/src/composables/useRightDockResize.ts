import { nextTick, onBeforeUnmount, onMounted, ref, watch, type Ref } from 'vue';

import {
  AGENT_DOCK_COLLAPSED_WIDTH_PX,
  clampAgentDockWidth,
  defaultAgentDockWidth,
  persistAgentDockWidth,
  readStoredAgentDockWidth,
} from '../lib/agent-dock-width';

type UseRightDockResizeOptions = {
  dockRef: Ref<HTMLElement | null>;
  collapsed?: Ref<boolean>;
};

export function useRightDockResize(options: UseRightDockResizeOptions) {
  const dockWidth = ref(readStoredAgentDockWidth() ?? defaultAgentDockWidth(window.innerWidth));
  const resizing = ref(false);

  function shellRoot(): HTMLElement | null {
    return options.dockRef.value?.closest('.console-shell--mockup') as HTMLElement | null;
  }

  function applyDockWidth(width: number): void {
    const clamped = clampAgentDockWidth(width, window.innerWidth);
    dockWidth.value = clamped;
    shellRoot()?.style.setProperty('--shell-agent-dock-width', `${clamped}px`);
  }

  function applyCollapsedDockWidth(): void {
    shellRoot()?.style.setProperty(
      '--shell-agent-dock-width',
      `${AGENT_DOCK_COLLAPSED_WIDTH_PX}px`,
    );
  }

  function syncDockWidthToShell(): void {
    if (options.collapsed?.value) {
      applyCollapsedDockWidth();
      return;
    }

    applyDockWidth(dockWidth.value);
  }

  function startDockResize(event: MouseEvent): void {
    if (event.button !== 0 || options.collapsed?.value) {
      return;
    }

    event.preventDefault();
    resizing.value = true;

    const onMove = (moveEvent: MouseEvent): void => {
      applyDockWidth(window.innerWidth - moveEvent.clientX);
    };

    const onUp = (): void => {
      resizing.value = false;
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
      document.removeEventListener('mousemove', onMove);
      document.removeEventListener('mouseup', onUp);
      persistAgentDockWidth(dockWidth.value);
    };

    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';
    document.addEventListener('mousemove', onMove);
    document.addEventListener('mouseup', onUp);
  }

  function resetDockWidth(): void {
    applyDockWidth(defaultAgentDockWidth(window.innerWidth));
    persistAgentDockWidth(dockWidth.value);
  }

  onMounted(() => {
    syncDockWidthToShell();
    window.addEventListener('resize', syncDockWidthToShell);
  });

  onBeforeUnmount(() => {
    window.removeEventListener('resize', syncDockWidthToShell);
    if (resizing.value) {
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    }
  });

  if (options.collapsed) {
    watch(
      () => options.collapsed?.value,
      async () => {
        await nextTick();
        syncDockWidthToShell();
        if (!options.collapsed?.value) {
          persistAgentDockWidth(dockWidth.value);
        }
      },
    );
  }

  return {
    dockWidth,
    resizing,
    resetDockWidth,
    startDockResize,
    syncDockWidthToShell,
  };
}

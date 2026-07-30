import {
  computed,
  onBeforeUnmount,
  onMounted,
  reactive,
  ref,
  type Ref,
} from 'vue';

import {
  applyGalaxyPanelResizeKeyAction,
  clampGalaxyPanelWidth,
  defaultGalaxyPanelWidths,
  GALAXY_LEFT_COLLAPSED_WIDTH_PX,
  persistGalaxyPanelWidths,
  persistGalaxyWorkspacesCollapsed,
  readStoredGalaxyPanelWidths,
  readStoredGalaxyWorkspacesCollapsed,
  resolveGalaxyPanelResizeKey,
  type GalaxyPanelKind,
  type GalaxyPanelWidths,
} from '../lib/galaxy-panel-widths';

type UseGalaxyPanelResizeOptions = {
  stageRef: Ref<HTMLElement | null>;
};

export function useGalaxyPanelResize(options: UseGalaxyPanelResizeOptions) {
  const viewportWidth = ref(
    typeof window !== 'undefined' ? window.innerWidth : 1280,
  );
  const stored = readStoredGalaxyPanelWidths();
  const defaults = defaultGalaxyPanelWidths(viewportWidth.value);
  const widths = reactive<GalaxyPanelWidths>({
    left: clampGalaxyPanelWidth(
      'left',
      stored?.left ?? defaults.left,
      viewportWidth.value,
    ),
    right: clampGalaxyPanelWidth(
      'right',
      stored?.right ?? defaults.right,
      viewportWidth.value,
    ),
    inspector: clampGalaxyPanelWidth(
      'inspector',
      stored?.inspector ?? defaults.inspector,
      viewportWidth.value,
    ),
  });
  const resizing = ref<GalaxyPanelKind | null>(null);
  /** Persisted operator preference (default expanded). */
  const userLeftCollapsed = ref(readStoredGalaxyWorkspacesCollapsed());
  /** Temporary collapse while VAXON speaks — does not overwrite preference. */
  const speechCollapseActive = ref(false);
  /** Operator expanded the rail while speech is forcing collapse. */
  const holdOpenDuringSpeech = ref(false);

  const leftCollapsed = computed(
    () =>
      userLeftCollapsed.value ||
      (speechCollapseActive.value && !holdOpenDuringSpeech.value),
  );

  function resolveWorkbench(): HTMLElement | null {
    const stage = options.stageRef.value;
    return (
      (stage?.closest('.region-center-workbench') as HTMLElement | null) ??
      (typeof document !== 'undefined'
        ? (document.querySelector('.region-center-workbench') as HTMLElement | null)
        : null)
    );
  }

  function applyCssVars(): void {
    const stage = options.stageRef.value;
    const leftWidth = leftCollapsed.value
      ? GALAXY_LEFT_COLLAPSED_WIDTH_PX
      : widths.left;
    const vars: Array<[string, string]> = [
      ['--galaxy-left-width', `${leftWidth}px`],
      ['--galaxy-right-width', `${widths.right}px`],
      ['--galaxy-inspector-width', `${widths.inspector}px`],
    ];
    if (stage) {
      for (const [name, value] of vars) {
        stage.style.setProperty(name, value);
      }
    }
    // Mirror onto the center workbench so floating captions share insets.
    const workbench = resolveWorkbench();
    if (workbench) {
      for (const [name, value] of vars) {
        workbench.style.setProperty(name, value);
      }
    }
  }

  function clearMirroredWorkbenchVars(): void {
    const workbench = resolveWorkbench();
    if (!workbench) {
      return;
    }
    workbench.style.removeProperty('--galaxy-left-width');
    workbench.style.removeProperty('--galaxy-right-width');
    workbench.style.removeProperty('--galaxy-inspector-width');
    workbench.style.removeProperty('--galaxy-bottom-reserve');
  }

  function setWidth(kind: GalaxyPanelKind, next: number, persist = true): void {
    if (kind === 'left' && leftCollapsed.value) {
      return;
    }
    widths[kind] = clampGalaxyPanelWidth(kind, next, viewportWidth.value);
    applyCssVars();
    if (persist) {
      persistGalaxyPanelWidths({ ...widths });
    }
  }

  function resetWidth(kind: GalaxyPanelKind): void {
    if (kind === 'left' && leftCollapsed.value) {
      setLeftCollapsed(false);
    }
    setWidth(kind, defaultGalaxyPanelWidths(viewportWidth.value)[kind]);
  }

  function setLeftCollapsed(collapsed: boolean): void {
    userLeftCollapsed.value = collapsed;
    persistGalaxyWorkspacesCollapsed(collapsed);
    if (!collapsed && speechCollapseActive.value) {
      holdOpenDuringSpeech.value = true;
    }
    if (collapsed) {
      holdOpenDuringSpeech.value = false;
    }
    applyCssVars();
  }

  function toggleLeftCollapsed(): void {
    if (speechCollapseActive.value && !userLeftCollapsed.value) {
      // Speech is forcing collapse: toggle hold-open without changing preference.
      holdOpenDuringSpeech.value = !holdOpenDuringSpeech.value;
      applyCssVars();
      return;
    }
    setLeftCollapsed(!userLeftCollapsed.value);
  }

  /** Collapse workspaces while VAXON speaks; restore preference when speech ends. */
  function setSpeechCollapseActive(active: boolean): void {
    speechCollapseActive.value = active;
    if (!active) {
      holdOpenDuringSpeech.value = false;
    }
    applyCssVars();
  }

  function startResize(kind: GalaxyPanelKind, edge: 'left' | 'right', event: MouseEvent): void {
    if (event.button !== 0) {
      return;
    }
    if (kind === 'left' && leftCollapsed.value) {
      return;
    }
    event.preventDefault();
    resizing.value = kind;
    const originX = event.clientX;
    const originWidth = widths[kind];

    const onMove = (moveEvent: MouseEvent): void => {
      const delta =
        edge === 'left'
          ? moveEvent.clientX - originX
          : originX - moveEvent.clientX;
      setWidth(kind, originWidth + delta, false);
    };

    const onUp = (): void => {
      resizing.value = null;
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
      document.removeEventListener('mousemove', onMove);
      document.removeEventListener('mouseup', onUp);
      persistGalaxyPanelWidths({ ...widths });
    };

    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';
    document.addEventListener('mousemove', onMove);
    document.addEventListener('mouseup', onUp);
  }

  function onResizeKeydown(
    kind: GalaxyPanelKind,
    edge: 'left' | 'right',
    event: KeyboardEvent,
  ): void {
    if (kind === 'left' && leftCollapsed.value) {
      return;
    }
    const action = resolveGalaxyPanelResizeKey(event.key, event.shiftKey, edge);
    if (!action) {
      return;
    }
    event.preventDefault();
    if (action.type === 'reset') {
      resetWidth(kind);
      return;
    }
    setWidth(
      kind,
      applyGalaxyPanelResizeKeyAction(kind, widths[kind], action, viewportWidth.value),
    );
  }

  function syncViewport(): void {
    viewportWidth.value = window.innerWidth;
    widths.left = clampGalaxyPanelWidth('left', widths.left, viewportWidth.value);
    widths.right = clampGalaxyPanelWidth('right', widths.right, viewportWidth.value);
    widths.inspector = clampGalaxyPanelWidth(
      'inspector',
      widths.inspector,
      viewportWidth.value,
    );
    applyCssVars();
  }

  onMounted(() => {
    applyCssVars();
    window.addEventListener('resize', syncViewport);
  });

  onBeforeUnmount(() => {
    window.removeEventListener('resize', syncViewport);
    clearMirroredWorkbenchVars();
    if (resizing.value) {
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    }
  });

  return {
    widths,
    resizing,
    leftCollapsed,
    setLeftCollapsed,
    toggleLeftCollapsed,
    setSpeechCollapseActive,
    startResize,
    onResizeKeydown,
    resetWidth,
    applyCssVars,
  };
}

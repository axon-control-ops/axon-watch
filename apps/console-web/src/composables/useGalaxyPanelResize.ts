import { onBeforeUnmount, onMounted, reactive, ref, type Ref } from 'vue';

import {
  applyGalaxyPanelResizeKeyAction,
  clampGalaxyPanelWidth,
  defaultGalaxyPanelWidths,
  persistGalaxyPanelWidths,
  readStoredGalaxyPanelWidths,
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

  function applyCssVars(): void {
    const stage = options.stageRef.value;
    if (!stage) {
      return;
    }
    stage.style.setProperty('--galaxy-left-width', `${widths.left}px`);
    stage.style.setProperty('--galaxy-right-width', `${widths.right}px`);
    stage.style.setProperty('--galaxy-inspector-width', `${widths.inspector}px`);
  }

  function setWidth(kind: GalaxyPanelKind, next: number, persist = true): void {
    widths[kind] = clampGalaxyPanelWidth(kind, next, viewportWidth.value);
    applyCssVars();
    if (persist) {
      persistGalaxyPanelWidths({ ...widths });
    }
  }

  function resetWidth(kind: GalaxyPanelKind): void {
    setWidth(kind, defaultGalaxyPanelWidths(viewportWidth.value)[kind]);
  }

  function startResize(kind: GalaxyPanelKind, edge: 'left' | 'right', event: MouseEvent): void {
    if (event.button !== 0) {
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
    if (resizing.value) {
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    }
  });

  return {
    widths,
    resizing,
    startResize,
    onResizeKeydown,
    resetWidth,
    applyCssVars,
  };
}

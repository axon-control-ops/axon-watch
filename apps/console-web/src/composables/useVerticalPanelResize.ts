import { computed, onBeforeUnmount, onMounted, ref, type Ref } from 'vue';

type SizeResolver = number | ((containerHeight: number) => number);

type UseVerticalPanelResizeOptions = {
  rootRef: Ref<HTMLElement | null>;
  cssVariable: `--${string}`;
  storageKey: string;
  defaultSize: SizeResolver;
  minSize: SizeResolver;
  maxSize: SizeResolver;
  growsUp?: boolean;
};

function resolveSize(value: SizeResolver, containerHeight: number): number {
  return typeof value === 'function' ? value(containerHeight) : value;
}

function storedSize(key: string): number | null {
  try {
    const raw = sessionStorage.getItem(key);
    const parsed = raw === null ? Number.NaN : Number(raw);
    return Number.isFinite(parsed) ? parsed : null;
  } catch {
    return null;
  }
}

function persistStoredSize(key: string, size: number): void {
  try {
    sessionStorage.setItem(key, String(size));
  } catch {
    // Resizing still works when browser storage is unavailable.
  }
}

function removeStoredSize(key: string): void {
  try {
    sessionStorage.removeItem(key);
  } catch {
    // The in-memory default remains authoritative.
  }
}

export function useVerticalPanelResize(options: UseVerticalPanelResizeOptions) {
  const persistedSize = storedSize(options.storageKey);
  const panelSize = ref(persistedSize ?? 0);
  const userSized = ref(persistedSize !== null);
  const resizing = ref(false);
  const containerHeight = ref(window.innerHeight);

  const ariaValueMin = computed(() =>
    Math.round(resolveSize(options.minSize, containerHeight.value)),
  );
  const ariaValueMax = computed(() =>
    Math.round(
      Math.max(
        ariaValueMin.value,
        resolveSize(options.maxSize, containerHeight.value),
      ),
    ),
  );

  function measureContainer(): number {
    return options.rootRef.value?.clientHeight || window.innerHeight;
  }

  function clampSize(size: number): number {
    const height = measureContainer();
    const min = resolveSize(options.minSize, height);
    const max = Math.max(min, resolveSize(options.maxSize, height));
    return Math.round(Math.min(max, Math.max(min, size)));
  }

  function applySize(size: number): void {
    containerHeight.value = measureContainer();
    panelSize.value = clampSize(size);
    options.rootRef.value?.style.setProperty(
      options.cssVariable,
      `${panelSize.value}px`,
    );
  }

  function defaultPanelSize(): number {
    return resolveSize(options.defaultSize, measureContainer());
  }

  function syncSize(): void {
    applySize(userSized.value ? panelSize.value : defaultPanelSize());
  }

  function persistSize(): void {
    userSized.value = true;
    persistStoredSize(options.storageKey, panelSize.value);
  }

  function resetSize(): void {
    userSized.value = false;
    removeStoredSize(options.storageKey);
    applySize(defaultPanelSize());
  }

  function startResize(event: MouseEvent): void {
    if (event.button !== 0) {
      return;
    }

    event.preventDefault();
    resizing.value = true;
    const startY = event.clientY;
    const startSize = panelSize.value;
    const direction = options.growsUp === false ? 1 : -1;

    const onMove = (moveEvent: MouseEvent): void => {
      applySize(startSize + (moveEvent.clientY - startY) * direction);
    };

    const onUp = (): void => {
      resizing.value = false;
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
      document.removeEventListener('mousemove', onMove);
      document.removeEventListener('mouseup', onUp);
      persistSize();
    };

    document.body.style.cursor = 'row-resize';
    document.body.style.userSelect = 'none';
    document.addEventListener('mousemove', onMove);
    document.addEventListener('mouseup', onUp);
  }

  function onResizeKeydown(event: KeyboardEvent): void {
    const step = event.shiftKey ? 32 : 8;
    let nextSize: number | null = null;

    if (event.key === 'ArrowUp') {
      nextSize = panelSize.value + (options.growsUp === false ? -step : step);
    } else if (event.key === 'ArrowDown') {
      nextSize = panelSize.value + (options.growsUp === false ? step : -step);
    } else if (event.key === 'Home') {
      nextSize = ariaValueMin.value;
    } else if (event.key === 'End') {
      nextSize = ariaValueMax.value;
    } else if (event.key === 'Enter') {
      event.preventDefault();
      resetSize();
      return;
    }

    if (nextSize === null) {
      return;
    }

    event.preventDefault();
    applySize(nextSize);
    persistSize();
  }

  onMounted(() => {
    syncSize();
    window.addEventListener('resize', syncSize);
  });

  onBeforeUnmount(() => {
    window.removeEventListener('resize', syncSize);
    if (resizing.value) {
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    }
  });

  return {
    panelSize,
    resizing,
    ariaValueMin,
    ariaValueMax,
    resetSize,
    startResize,
    onResizeKeydown,
    syncSize,
  };
}

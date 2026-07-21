import { nextTick, onMounted, onUnmounted, ref, type Ref } from 'vue';

function wheelDeltaPixels(event: WheelEvent): number {
  if (event.deltaMode === WheelEvent.DOM_DELTA_LINE) {
    return event.deltaY * 16;
  }
  if (event.deltaMode === WheelEvent.DOM_DELTA_PAGE) {
    return event.deltaY * window.innerHeight;
  }
  return event.deltaY;
}

function targetHasScrollableRoom(
  target: EventTarget | null,
  container: HTMLElement,
  deltaY: number,
): boolean {
  let element = target instanceof HTMLElement ? target : null;
  while (element && element !== container) {
    if (element.scrollHeight > element.clientHeight + 1) {
      const canScrollUp = deltaY < 0 && element.scrollTop > 0;
      const canScrollDown =
        deltaY > 0 && element.scrollTop + element.clientHeight < element.scrollHeight - 1;
      if (canScrollUp || canScrollDown) {
        return true;
      }
    }
    element = element.parentElement;
  }
  return false;
}

export function resolveConversationScrollContainer(
  root: HTMLElement | null,
  list: HTMLElement | null,
): HTMLElement | null {
  if (!root) {
    return null;
  }

  const transcript = root.closest('.agent-dock__transcript');
  if (transcript instanceof HTMLElement) {
    return transcript;
  }

  if (list instanceof HTMLElement) {
    return list;
  }

  const seamBody = root.closest('.hud-seam__body');
  if (seamBody instanceof HTMLElement) {
    return seamBody;
  }

  return root;
}

export function useConversationSeamScroll(options: {
  rootRef: Ref<HTMLElement | null>;
  listRef: Ref<HTMLElement | null>;
  onContentChange: () => void;
}) {
  const stickToBottom = ref(true);
  let resizeObserver: ResizeObserver | null = null;
  let scrollContainer: HTMLElement | null = null;

  function scrollContainerElement(): HTMLElement | null {
    return resolveConversationScrollContainer(options.rootRef.value, options.listRef.value);
  }

  function isNearBottom(container: HTMLElement): boolean {
    return container.scrollHeight - container.scrollTop - container.clientHeight < 48;
  }

  function updateStickToBottom(): void {
    const container = scrollContainerElement();
    if (!container) {
      stickToBottom.value = true;
      return;
    }
    stickToBottom.value = isNearBottom(container);
  }

  async function scrollToLatest(reason = 'explicit'): Promise<void> {
    await nextTick();
    const container = scrollContainerElement();
    if (!container) {
      return;
    }
    const previousTop = container.scrollTop;
    const targetTop = container.scrollHeight;
    if (Math.abs(targetTop - previousTop) > 1) {
      // #region agent log
      fetch('http://127.0.0.1:7706/ingest/90bcaec2-2b39-4d4a-84b5-157c12735440',{method:'POST',headers:{'Content-Type':'application/json','X-Debug-Session-Id':'fc0b35'},body:JSON.stringify({sessionId:'fc0b35',runId:'conversation-scroll',hypothesisId:'H8',location:'useConversationSeamScroll.ts:scrollToLatest',message:'conversation transcript auto-scroll requested',data:{reason,previousTop:Math.round(previousTop),targetTop:Math.round(targetTop),clientHeight:Math.round(container.clientHeight),scrollHeight:Math.round(container.scrollHeight),stickToBottom:stickToBottom.value},timestamp:Date.now()})}).catch(()=>{});
      // #endregion
    }
    container.scrollTop = container.scrollHeight;
    stickToBottom.value = true;
  }

  async function scrollToLatestIfPinned(reason = 'pinned'): Promise<void> {
    if (!stickToBottom.value) {
      return;
    }
    await scrollToLatest(reason);
  }

  function bindScrollContainer(): void {
    const next = scrollContainerElement();
    if (scrollContainer === next) {
      return;
    }
    if (scrollContainer) {
      scrollContainer.removeEventListener('scroll', updateStickToBottom);
    }
    scrollContainer = next;
    if (scrollContainer) {
      scrollContainer.addEventListener('scroll', updateStickToBottom, { passive: true });
    }
  }

  function handleWheel(event: WheelEvent): void {
    const container = scrollContainerElement();
    if (!container || targetHasScrollableRoom(event.target, container, event.deltaY)) {
      return;
    }

    const delta = wheelDeltaPixels(event);
    if (!delta) {
      return;
    }
    event.preventDefault();
    container.scrollTop += delta;
    updateStickToBottom();
  }

  function handleContentChange(): void {
    options.onContentChange();
    bindScrollContainer();
    void scrollToLatestIfPinned('content-change');
  }

  onMounted(() => {
    bindScrollContainer();
    resizeObserver = new ResizeObserver(() => {
      void scrollToLatestIfPinned('resize-observer');
    });
    if (options.rootRef.value) {
      resizeObserver.observe(options.rootRef.value);
    }
    if (options.listRef.value) {
      resizeObserver.observe(options.listRef.value);
    }
    void scrollToLatest('mount');
  });

  onUnmounted(() => {
    resizeObserver?.disconnect();
    resizeObserver = null;
    if (scrollContainer) {
      scrollContainer.removeEventListener('scroll', updateStickToBottom);
      scrollContainer = null;
    }
  });

  return {
    stickToBottom,
    handleWheel,
    handleContentChange,
    scrollToLatest,
    scrollToLatestIfPinned,
    bindScrollContainer,
  };
}

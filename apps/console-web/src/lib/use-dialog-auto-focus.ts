import { nextTick, ref, watch, type Ref } from 'vue';

export type DialogAutoFocusOptions = {
  onEscape?: () => void;
};

function isFocusableElement(node: unknown): node is HTMLElement {
  return Boolean(
    node &&
      typeof node === 'object' &&
      'focus' in node &&
      typeof (node as HTMLElement).focus === 'function',
  );
}

/** Focus a modal dialog root when it opens; restore focus and handle Escape on close. */
export function useDialogAutoFocus(
  isOpen: Ref<boolean>,
  options: DialogAutoFocusOptions = {},
): Ref<HTMLElement | null> {
  const dialogRef = ref<HTMLElement | null>(null);
  let restoreFocusTarget: HTMLElement | null = null;
  let previousBodyOverflow: string | null = null;

  watch(isOpen, async (open, _wasOpen, onCleanup) => {
    if (open) {
      if (typeof document !== 'undefined') {
        restoreFocusTarget = isFocusableElement(document.activeElement)
          ? document.activeElement
          : null;

        if (document.body) {
          previousBodyOverflow = document.body.style.overflow;
          document.body.style.overflow = 'hidden';
          onCleanup(() => {
            document.body.style.overflow = previousBodyOverflow ?? '';
            previousBodyOverflow = null;
          });
        }
      }

      const onEscape = options.onEscape;
      if (onEscape && typeof window !== 'undefined') {
        const handleEscape = (event: KeyboardEvent) => {
          if (event.key === 'Escape') {
            onEscape();
          }
        };
        window.addEventListener('keydown', handleEscape);
        onCleanup(() => {
          window.removeEventListener('keydown', handleEscape);
        });
      }

      await nextTick();
      dialogRef.value?.focus();
      return;
    }

    const target = restoreFocusTarget;
    restoreFocusTarget = null;
    if (!target) {
      return;
    }
    await nextTick();
    if (typeof document !== 'undefined' && document.contains(target)) {
      target.focus();
    }
  });

  return dialogRef;
}

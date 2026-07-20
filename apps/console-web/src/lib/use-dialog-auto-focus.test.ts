import { nextTick, ref } from 'vue';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { useDialogAutoFocus } from './use-dialog-auto-focus';

describe('useDialogAutoFocus', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('focuses the dialog root when opened', async () => {
    const isOpen = ref(false);
    const dialogRef = useDialogAutoFocus(isOpen);
    const focus = vi.fn();

    dialogRef.value = { focus } as unknown as HTMLElement;
    isOpen.value = true;

    await nextTick();
    await nextTick();

    expect(focus).toHaveBeenCalledTimes(1);
  });

  it('does not focus when the dialog stays closed', async () => {
    const isOpen = ref(false);
    const dialogRef = useDialogAutoFocus(isOpen);
    const focus = vi.fn();

    dialogRef.value = { focus } as unknown as HTMLElement;

    await nextTick();

    expect(focus).not.toHaveBeenCalled();
  });

  it('restores focus to the previously focused element when closed', async () => {
    const trigger = { focus: vi.fn() };
    vi.stubGlobal('document', {
      activeElement: trigger,
      contains: vi.fn(() => true),
    });

    const isOpen = ref(false);
    const dialogRef = useDialogAutoFocus(isOpen);
    const dialogFocus = vi.fn();

    dialogRef.value = { focus: dialogFocus } as unknown as HTMLElement;
    isOpen.value = true;

    await nextTick();
    await nextTick();

    isOpen.value = false;
    await nextTick();
    await nextTick();

    expect(trigger.focus).toHaveBeenCalledTimes(1);
  });

  it('locks body scroll while open and restores it on close', async () => {
    const body = { style: { overflow: 'auto' } };
    vi.stubGlobal('document', {
      activeElement: null,
      body,
      contains: vi.fn(() => true),
    });

    const isOpen = ref(false);
    const dialogRef = useDialogAutoFocus(isOpen);
    dialogRef.value = { focus: vi.fn() } as unknown as HTMLElement;

    isOpen.value = true;
    await nextTick();

    expect(body.style.overflow).toBe('hidden');

    isOpen.value = false;
    await nextTick();
    await nextTick();

    expect(body.style.overflow).toBe('auto');
  });

  it('calls onEscape when Escape is pressed while open', async () => {
    const listeners: Array<(event: KeyboardEvent) => void> = [];
    vi.stubGlobal('window', {
      addEventListener: (_type: string, listener: (event: KeyboardEvent) => void) => {
        listeners.push(listener);
      },
      removeEventListener: (_type: string, listener: (event: KeyboardEvent) => void) => {
        const index = listeners.indexOf(listener);
        if (index >= 0) {
          listeners.splice(index, 1);
        }
      },
    });

    const isOpen = ref(false);
    const onEscape = vi.fn();

    useDialogAutoFocus(isOpen, { onEscape });
    isOpen.value = true;
    await nextTick();

    listeners[0]?.({ key: 'Escape' } as KeyboardEvent);
    expect(onEscape).toHaveBeenCalledTimes(1);

    isOpen.value = false;
    await nextTick();

    listeners[0]?.({ key: 'Escape' } as KeyboardEvent);
    expect(onEscape).toHaveBeenCalledTimes(1);
  });
});

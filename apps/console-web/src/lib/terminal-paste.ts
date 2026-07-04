/** Forward clipboard paste directly to the PTY without xterm bracketed-paste mangling. */

export function attachTerminalPasteHandler(
  container: HTMLElement,
  sendInput: (data: string) => void,
): () => void {
  const onPaste = (event: ClipboardEvent): void => {
    const text = event.clipboardData?.getData('text/plain') ?? '';
    if (!text) {
      return;
    }

    event.preventDefault();
    event.stopPropagation();
    sendInput(text);
  };

  container.addEventListener('paste', onPaste, true);
  return () => {
    container.removeEventListener('paste', onPaste, true);
  };
}

/** Focus the Agent Dock composer input after restoring a draft (Cursor Edit parity). */

export function focusAgentDockComposerInput(): void {
  requestAnimationFrame(() => {
    const input = document.getElementById('agent-dock-composer-input') as HTMLTextAreaElement | null;
    if (!input) {
      return;
    }
    input.focus();
    const end = input.value.length;
    input.setSelectionRange(end, end);
  });
}

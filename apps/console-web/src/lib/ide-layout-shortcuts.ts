export type IdeLayoutShortcutAction =
  | 'toggle-explorer'
  | 'toggle-agent-dock'
  | 'toggle-terminal'
  | 'open-search'
  | 'open-source-control';

export type IdeLayoutShortcutContext = {
  layoutMode: string;
  modKey: boolean;
  shiftKey: boolean;
  key: string;
  /** True for inputs, textareas, xterm, command seam — never steal keys there. */
  formOrTerminalEditable: boolean;
  /** True for any editable surface including contenteditable editors. */
  editableTarget: boolean;
};

function isShellLayoutMode(layoutMode: string): boolean {
  return layoutMode === 'ide' || layoutMode === 'operator';
}

/** Resolve shell layout keyboard shortcuts (Ctrl/Cmd+B, Shift+G, J, \\). */
export function resolveIdeLayoutShortcut(
  context: IdeLayoutShortcutContext,
): IdeLayoutShortcutAction | null {
  if (!isShellLayoutMode(context.layoutMode) || !context.modKey) {
    return null;
  }

  const normalizedKey = context.key.toLowerCase();

  // Mod+J always toggles the workbench terminal, including inside the markdown
  // editor (TipTap AI otherwise steals it). Skip only real form/xterm fields.
  if (normalizedKey === 'j' && !context.shiftKey) {
    if (context.formOrTerminalEditable) {
      return null;
    }
    return 'toggle-terminal';
  }

  if (context.editableTarget) {
    return null;
  }

  if (context.layoutMode !== 'ide') {
    return null;
  }

  if (context.shiftKey && normalizedKey === 'f') {
    return 'open-search';
  }

  if (context.shiftKey && normalizedKey === 'g') {
    return 'open-source-control';
  }

  if (normalizedKey === 'b' && !context.shiftKey) {
    return 'toggle-explorer';
  }

  if (context.key === '\\') {
    return 'toggle-agent-dock';
  }

  return null;
}

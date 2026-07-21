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
  editableTarget: boolean;
};

function isShellLayoutMode(layoutMode: string): boolean {
  return layoutMode === 'ide' || layoutMode === 'operator';
}

/** Resolve shell layout keyboard shortcuts (Ctrl/Cmd+B, Shift+G, J, \\). */
export function resolveIdeLayoutShortcut(
  context: IdeLayoutShortcutContext,
): IdeLayoutShortcutAction | null {
  if (!isShellLayoutMode(context.layoutMode) || context.editableTarget || !context.modKey) {
    return null;
  }

  const normalizedKey = context.key.toLowerCase();

  if (normalizedKey === 'j') {
    return 'toggle-terminal';
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

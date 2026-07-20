export type IdeLayoutShortcutAction =
  | 'toggle-explorer'
  | 'toggle-agent-dock'
  | 'toggle-terminal';

export type IdeLayoutShortcutContext = {
  layoutMode: string;
  modKey: boolean;
  key: string;
  editableTarget: boolean;
};

function isShellLayoutMode(layoutMode: string): boolean {
  return layoutMode === 'ide' || layoutMode === 'operator';
}

/** Resolve shell layout keyboard shortcuts (Ctrl/Cmd+B, J, \\). */
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

  if (normalizedKey === 'b') {
    return 'toggle-explorer';
  }

  if (context.key === '\\') {
    return 'toggle-agent-dock';
  }

  return null;
}

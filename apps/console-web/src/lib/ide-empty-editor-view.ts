export type IdeEmptyEditorStepAction =
  | 'explorer'
  | 'search'
  | 'new-file'
  | 'agent';

export type IdeEmptyEditorStep = {
  label: string;
  detail: string;
  shortcut?: string;
  /** When set, the step is clickable and dispatches this action. */
  action?: IdeEmptyEditorStepAction;
};

export type IdeEmptyEditorView = {
  title: string;
  subtitle: string;
  steps: IdeEmptyEditorStep[];
};

/** Progressive copy for the IDE workbench when no editor tab is open. */
export function buildIdeEmptyEditorView(input: {
  hasWorkspace: boolean;
}): IdeEmptyEditorView {
  if (!input.hasWorkspace) {
    return {
      title: 'Choose a workspace to start editing',
      subtitle: 'Pick a project from the top bar, then open files from Explorer or Search.',
      steps: [
        {
          label: 'Select workspace',
          detail: 'Use the workspace picker in the top bar to bind a project root.',
        },
        {
          label: 'Open Explorer',
          detail: 'Press Ctrl/Cmd+B to browse files once a workspace is active.',
          shortcut: 'Ctrl/Cmd+B',
          action: 'explorer',
        },
        {
          label: 'Ask the agent',
          detail: 'Expand the agent dock (Ctrl/Cmd+\\) to describe what you want to build.',
          shortcut: 'Ctrl/Cmd+\\',
          action: 'agent',
        },
      ],
    };
  }

  return {
    title: 'Open a file to start editing',
    subtitle: 'Browse the workspace tree, search by path, or ask the agent to open a file for you.',
    steps: [
      {
        label: 'Explorer',
        detail: 'Browse folders and double-click a file to open it in the editor.',
        shortcut: 'Ctrl/Cmd+B',
        action: 'explorer',
      },
      {
        label: 'Search',
        detail: 'Filter workspace paths when you know part of the filename.',
        shortcut: 'Ctrl/Cmd+Shift+F',
        action: 'search',
      },
      {
        label: 'New file',
        detail: 'Opens Explorer with an inline name field — press Enter to create.',
        action: 'new-file',
      },
      {
        label: 'Agent dock',
        detail: 'Describe changes in the composer — edits can open as review tabs.',
        shortcut: 'Ctrl/Cmd+\\',
        action: 'agent',
      },
    ],
  };
}

import { describe, expect, it } from 'vitest';

import { buildIdeEmptyEditorView } from './ide-empty-editor-view';

describe('buildIdeEmptyEditorView', () => {
  it('guides workspace selection when no project is active', () => {
    const view = buildIdeEmptyEditorView({ hasWorkspace: false });

    expect(view.title).toContain('Choose a workspace');
    expect(view.steps.map((step) => step.label)).toEqual([
      'Select workspace',
      'Open Explorer',
      'Ask the agent',
    ]);
  });

  it('guides file open flows when a workspace is active', () => {
    const view = buildIdeEmptyEditorView({ hasWorkspace: true });

    expect(view.title).toContain('Open a file');
    expect(view.steps.map((step) => step.label)).toEqual([
      'Explorer',
      'Search',
      'New file',
      'Agent dock',
    ]);
    expect(view.steps[0]?.shortcut).toBe('Ctrl/Cmd+B');
    expect(view.steps[2]?.action).toBe('new-file');
  });
});

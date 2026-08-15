import { describe, expect, it } from 'vitest';

import { resolveIdeActivityBarSelectAction } from './ide-activity-bar-select';

const sidebarViews = new Set(['explorer', 'search', 'git', 'run', 'team']);

describe('resolveIdeActivityBarSelectAction', () => {
  it('collapses explorer when re-clicking the open explorer view', () => {
    expect(
      resolveIdeActivityBarSelectAction({
        view: 'explorer',
        currentView: 'explorer',
        explorerCollapsed: false,
        agentDockCollapsed: false,
        sidebarViews,
      }),
    ).toBe('toggle-explorer');
  });

  it('opens explorer when it is collapsed', () => {
    expect(
      resolveIdeActivityBarSelectAction({
        view: 'explorer',
        currentView: 'explorer',
        explorerCollapsed: true,
        agentDockCollapsed: true,
        sidebarViews,
      }),
    ).toBe('set-view');
  });

  it('collapses agent dock when re-clicking while expanded', () => {
    expect(
      resolveIdeActivityBarSelectAction({
        view: 'agent',
        currentView: 'explorer',
        explorerCollapsed: false,
        agentDockCollapsed: false,
        sidebarViews,
      }),
    ).toBe('toggle-agent');
  });

  it('expands agent dock when collapsed', () => {
    expect(
      resolveIdeActivityBarSelectAction({
        view: 'agent',
        currentView: 'explorer',
        explorerCollapsed: false,
        agentDockCollapsed: true,
        sidebarViews,
      }),
    ).toBe('open-agent-dock');
  });

  it('toggles the workbench terminal when it is already visible', () => {
    expect(
      resolveIdeActivityBarSelectAction({
        view: 'terminal',
        currentView: 'terminal',
        explorerCollapsed: false,
        agentDockCollapsed: true,
        terminalPanelVisible: true,
        sidebarViews,
      }),
    ).toBe('toggle-terminal');
  });

  it('opens team without collapsing when explorer is already collapsed', () => {
    expect(
      resolveIdeActivityBarSelectAction({
        view: 'team',
        currentView: 'explorer',
        explorerCollapsed: true,
        agentDockCollapsed: true,
        sidebarViews,
      }),
    ).toBe('set-view');
  });
});

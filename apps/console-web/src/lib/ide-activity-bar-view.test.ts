import { describe, expect, it } from 'vitest';

import type { CompanyEmployeeRecord } from '../contracts/canonical';
import {
  buildIdeActivityBarTeamAttention,
  ideActivityBarExplorerAriaLabel,
  ideActivityBarExplorerTitle,
  ideActivityBarGitAriaLabel,
  ideActivityBarGitNeedsAttention,
  ideActivityBarGitTitle,
  ideActivityBarRunAriaLabel,
  ideActivityBarRunNeedsAttention,
  ideActivityBarRunTitle,
  ideActivityBarSearchAriaLabel,
  ideActivityBarSearchNeedsAttention,
  ideActivityBarSearchTitle,
  ideActivityBarSidebarAriaLabel,
  ideActivityBarSidebarTitle,
  ideActivityBarTeamAriaLabel,
  ideActivityBarTeamNeedsAttention,
  ideActivityBarTeamTitle,
} from './ide-activity-bar-view';

function employee(overrides: Partial<CompanyEmployeeRecord> = {}): CompanyEmployeeRecord {
  return {
    employee_id: 'e1',
    workspace_id: 'workspace_demo',
    name: 'Shell Craft',
    role: 'frontend',
    role_label: 'UI/UX',
    schedule: 'continuous',
    schedule_label: 'Continuous',
    status: 'idle',
    owns: 'console UI/UX, dock, and shell polish',
    enabled: true,
    primary: false,
    ...overrides,
  };
}

describe('ide activity bar view', () => {
  it('names the explorer button with the sidebar shortcut', () => {
    expect(ideActivityBarExplorerTitle(false)).toBe('Explorer (Ctrl/Cmd+B)');
    expect(ideActivityBarExplorerTitle(true)).toBe(
      'Explorer (Ctrl/Cmd+B) · Click to collapse',
    );
    expect(ideActivityBarExplorerAriaLabel(false)).toBe('Expand explorer sidebar');
    expect(ideActivityBarExplorerAriaLabel(true)).toBe('Collapse explorer sidebar');
  });

  it('names sidebar panel buttons with collapse hints when expanded', () => {
    expect(ideActivityBarSidebarTitle('search', false)).toBe('Search (Ctrl/Cmd+Shift+F)');
    expect(ideActivityBarSidebarTitle('search', true)).toBe(
      'Search (Ctrl/Cmd+Shift+F) · Click to collapse',
    );
    expect(ideActivityBarSidebarAriaLabel('git', false)).toBe('Expand source control sidebar');
    expect(ideActivityBarSidebarAriaLabel('team', true)).toBe('Collapse workspace team sidebar');
  });

  it('surfaces watch offline on the Run activity button before stale counts', () => {
    const offline = {
      watchConnected: false,
      requiredConnectorsUnavailable: 0,
      legacyConnectorGlanceVisible: false,
    };
    expect(ideActivityBarRunNeedsAttention(offline)).toBe(true);
    expect(ideActivityBarRunTitle(false, offline)).toBe('Run · Watch offline');
    expect(ideActivityBarRunAriaLabel(false, offline)).toBe(
      'Expand run sidebar, watch offline',
    );
  });

  it('surfaces connector attention on the Run activity button', () => {
    const required = {
      watchConnected: true,
      requiredConnectorsUnavailable: 2,
      legacyConnectorGlanceVisible: false,
    };
    expect(ideActivityBarRunNeedsAttention(required)).toBe(true);
    expect(ideActivityBarRunTitle(false, required)).toBe(
      'Run · 2 required connectors down',
    );
    expect(ideActivityBarRunAriaLabel(true, required)).toBe(
      'Collapse run sidebar, 2 required connectors down',
    );

    const legacy = {
      watchConnected: true,
      requiredConnectorsUnavailable: 0,
      legacyConnectorGlanceVisible: true,
    };
    expect(ideActivityBarRunNeedsAttention(legacy)).toBe(true);
    expect(ideActivityBarRunTitle(false, legacy)).toContain('Legacy Axon Local offline');

    const healthy = {
      watchConnected: true,
      requiredConnectorsUnavailable: 0,
      legacyConnectorGlanceVisible: false,
    };
    expect(ideActivityBarRunNeedsAttention(healthy)).toBe(false);
    expect(ideActivityBarRunTitle(false, healthy)).toBe('Run');
  });

  it('surfaces failed-shift attention on the Team activity button', () => {
    const failed = [
      employee({
        last_outcome: 'failed',
        last_outcome_detail: 'Agent exited with status 1',
      }),
    ];

    expect(ideActivityBarTeamNeedsAttention([])).toBe(false);
    expect(ideActivityBarTeamNeedsAttention(failed)).toBe(true);
    expect(buildIdeActivityBarTeamAttention(failed)).toEqual({
      count: 1,
      tone: 'failure',
      hint: '1 teammate needs attention — tap to open their dock, then Try again',
    });
    expect(ideActivityBarTeamTitle(false, failed)).toBe(
      'Workspace team · 1 teammate needs attention — tap to open their dock, then Try again',
    );
    expect(ideActivityBarTeamTitle(true, [failed[0], { ...failed[0], employee_id: 'e2' }])).toBe(
      'Workspace team · Click to collapse · 2 teammates need attention — tap to open a failed dock, then Try again',
    );
    expect(ideActivityBarTeamAriaLabel(false, failed)).toBe(
      'Expand workspace team sidebar, 1 teammate needs attention — tap to open their dock, then try again',
    );
  });

  it('surfaces interrupted-shift attention on the Team activity button', () => {
    const interrupted = [
      employee({
        last_outcome: 'failed',
        last_outcome_detail: 'Run interrupted by control-plane restart',
      }),
    ];

    expect(buildIdeActivityBarTeamAttention(interrupted)).toEqual({
      count: 1,
      tone: 'interrupted',
      hint: '1 teammate has an interrupted job — select them and tap Continue',
    });
    expect(ideActivityBarTeamTitle(false, interrupted)).toContain('interrupted job');
    expect(ideActivityBarTeamTitle(false, interrupted)).toContain('Continue');
  });

  it('surfaces mixed attention when both failed and interrupted teammates need help', () => {
    const mixed = [
      employee({
        employee_id: 'e1',
        last_outcome: 'failed',
        last_outcome_detail: 'Agent exited with status 1',
      }),
      employee({
        employee_id: 'e2',
        name: 'Backend Bot',
        last_outcome: 'failed',
        last_outcome_detail: 'Run interrupted by control-plane restart',
      }),
    ];

    expect(buildIdeActivityBarTeamAttention(mixed)).toEqual({
      count: 2,
      tone: 'mixed',
      hint: '2 teammates need attention after a failed or interrupted job',
    });
    expect(ideActivityBarTeamTitle(false, mixed)).toContain('failed or interrupted job');
  });

  it('surfaces unsaved-file attention on the Source Control activity button', () => {
    expect(ideActivityBarGitNeedsAttention(0)).toBe(false);
    expect(ideActivityBarGitNeedsAttention(2)).toBe(true);
    expect(ideActivityBarGitTitle(false, 0)).toBe('Source Control (Ctrl/Cmd+Shift+G)');
    expect(ideActivityBarGitTitle(false, 1)).toBe(
      'Source Control (Ctrl/Cmd+Shift+G) · 1 unsaved file',
    );
    expect(ideActivityBarGitTitle(true, 3)).toBe(
      'Source Control (Ctrl/Cmd+Shift+G) · Click to collapse · 3 unsaved files',
    );
    expect(ideActivityBarGitAriaLabel(false, 2)).toBe(
      'Expand source control sidebar, 2 unsaved files',
    );
  });

  it('surfaces load-failure attention on the Search activity button', () => {
    const attention = { loadState: 'error' as const, hasWorkspace: true };
    expect(ideActivityBarSearchNeedsAttention(attention)).toBe(true);
    expect(ideActivityBarSearchTitle(false, attention)).toContain('failed to load');
    expect(ideActivityBarSearchTitle(false, attention)).toContain('Ctrl/Cmd+Shift+F');
    expect(ideActivityBarSearchAriaLabel(true, attention).toLowerCase()).toContain(
      'collapse search sidebar',
    );
    expect(ideActivityBarSearchAriaLabel(true, attention).toLowerCase()).toContain('retry');

    expect(
      ideActivityBarSearchNeedsAttention({
        loadState: 'loaded',
        hasWorkspace: true,
      }),
    ).toBe(false);
    expect(
      ideActivityBarSearchTitle(false, {
        loadState: 'loaded',
        hasWorkspace: true,
      }),
    ).toBe('Search (Ctrl/Cmd+Shift+F)');
  });
});

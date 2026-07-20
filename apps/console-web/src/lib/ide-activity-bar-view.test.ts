import { describe, expect, it } from 'vitest';

import {
  ideActivityBarExplorerAriaLabel,
  ideActivityBarExplorerTitle,
  ideActivityBarRunAriaLabel,
  ideActivityBarRunNeedsAttention,
  ideActivityBarRunTitle,
  ideActivityBarSidebarAriaLabel,
  ideActivityBarSidebarTitle,
} from './ide-activity-bar-view';

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
    expect(ideActivityBarSidebarTitle('search', false)).toBe('Search');
    expect(ideActivityBarSidebarTitle('search', true)).toBe('Search · Click to collapse');
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
});

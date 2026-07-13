import { describe, expect, it } from 'vitest';

import { resolveBrainGalaxyNodeSelection } from './brain-galaxy-node-selection';

describe('resolveBrainGalaxyNodeSelection', () => {
  it('returns null focus when no node is selected', () => {
    expect(resolveBrainGalaxyNodeSelection(null)).toEqual({
      focus: null,
      evidenceNodeId: null,
    });
  });

  it('opens evidence and focuses conversation for workspace nodes', () => {
    expect(
      resolveBrainGalaxyNodeSelection({
        node_id: 'ws_workspace_dashpro',
        kind: 'workspace',
        label: 'DashPro',
        tone: 'critical',
        workspace_id: 'workspace_dashpro',
        detail: '2 signals',
      }),
    ).toEqual({
      focus: {
        nodeId: 'ws_workspace_dashpro',
        workspaceId: 'workspace_dashpro',
        signalId: null,
        label: 'DashPro',
      },
      evidenceNodeId: 'ws_workspace_dashpro',
    });
  });

  it('strips the sig_ prefix for signal evidence and conversation focus', () => {
    expect(
      resolveBrainGalaxyNodeSelection({
        node_id: 'sig_signal_monitor_dashpro_sentry_critical',
        kind: 'signal',
        label: 'DashPro Sentry critical',
        tone: 'critical',
        workspace_id: 'workspace_dashpro',
        detail: 'critical',
      }),
    ).toEqual({
      focus: {
        nodeId: 'sig_signal_monitor_dashpro_sentry_critical',
        workspaceId: 'workspace_dashpro',
        signalId: 'signal_monitor_dashpro_sentry_critical',
        label: 'DashPro Sentry critical',
      },
      evidenceNodeId: 'sig_signal_monitor_dashpro_sentry_critical',
    });
  });
});

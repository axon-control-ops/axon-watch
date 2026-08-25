import { describe, expect, it } from 'vitest';

import { workspaceAgentLabel } from './workspace-agent-label';

describe('workspaceAgentLabel', () => {
  it('returns the agent name when idle', () => {
    expect(
      workspaceAgentLabel({
        agent_id: 'workspace-agent-workspace_axon_watch',
        workspace_id: 'workspace_axon_watch',
        agent_name: 'Axon-X Workspace Agent',
        agent_key: 'axon_watch_workspace_agent',
        role: 'workspace_agent',
        status: 'idle',
        owns: 'axon-watch work',
        enabled: true,
      }),
    ).toBe('Axon-X Workspace Agent');
  });

  it('includes status when the agent is busy', () => {
    expect(
      workspaceAgentLabel({
        agent_id: 'workspace-agent-workspace_dashpro',
        workspace_id: 'workspace_dashpro',
        agent_name: 'DashPro Workspace Agent',
        agent_key: 'dashpro_workspace_agent',
        role: 'workspace_agent',
        status: 'executing',
        owns: 'DashPro work',
        enabled: true,
      }),
    ).toBe('DashPro Workspace Agent · executing');
  });

  it('does not surface thought or status-dump prose as picker meta', () => {
    expect(
      workspaceAgentLabel({
        agent_id: 'workspace-agent-workspace_dashpro',
        workspace_id: 'workspace_dashpro',
        agent_name: 'DashPro Workspace Agent',
        agent_key: 'dashpro_workspace_agent',
        role: 'workspace_agent',
        // Runtime payloads can be polluted; picker must ignore prose.
        status:
          'Thought — All tests pass. A critical review summary follows. Locked the graduation confirmation aut' as
            'executing',
        owns: 'DashPro work',
        enabled: true,
      }),
    ).toBe('DashPro Workspace Agent');
  });
});

import { describe, expect, it } from 'vitest';

import { resolveConversationNavigationIntent, workspaceGalaxyNodeId } from './conversation-intents';

const WORKSPACES = [
  { workspace_id: 'workspace_dashpro', display_name: 'DashPro' },
  { workspace_id: 'workspace_axon', display_name: 'Axon Watch' },
];

describe('resolveConversationNavigationIntent', () => {
  it('focuses attention locally', () => {
    expect(resolveConversationNavigationIntent('open attention', WORKSPACES)).toEqual({
      kind: 'focus_attention',
      reply: 'Opening Attention for you.',
    });
  });

  it('opens the operator briefing panel', () => {
    expect(resolveConversationNavigationIntent('open VAXON briefing', WORKSPACES)).toEqual({
      kind: 'focus_briefing',
      reply: 'Opening the briefing for you.',
    });
  });

  it('switches to grid view', () => {
    expect(resolveConversationNavigationIntent('grid view', WORKSPACES)).toEqual({
      kind: 'switch_center_view',
      centerView: 'mission',
      reply: 'Switching to fleet grid view.',
    });
  });

  it('enters a workspace coding surface on open', () => {
    expect(resolveConversationNavigationIntent('Open DashPro workspace', WORKSPACES)).toEqual({
      kind: 'enter_workspace',
      workspaceId: 'workspace_dashpro',
      reply: 'Opening DashPro.',
    });
  });

  it('focuses a workspace on Mission Control without entering IDE', () => {
    expect(resolveConversationNavigationIntent('show me DashPro', WORKSPACES)).toEqual({
      kind: 'focus_workspace',
      workspaceId: 'workspace_dashpro',
      reply: 'DashPro is on deck.',
    });
  });

  it('does not treat fleet health questions as grid navigation', () => {
    expect(
      resolveConversationNavigationIntent(
        'Explain the current operator fleet health in detail — which workspaces need attention and why.',
        WORKSPACES,
      ),
    ).toBeNull();
  });

  it('switches to fleet grid on explicit fleet grid phrasing', () => {
    expect(resolveConversationNavigationIntent('show fleet grid', WORKSPACES)).toEqual({
      kind: 'switch_center_view',
      centerView: 'mission',
      reply: 'Switching to fleet grid view.',
    });
  });

  it('does not treat descriptive galaxy mentions as brain navigation', () => {
    expect(
      resolveConversationNavigationIntent('what nodes are in the brain galaxy right now?', WORKSPACES),
    ).toBeNull();
  });

  it('maps workspace ids to galaxy node ids', () => {
    expect(workspaceGalaxyNodeId('workspace_dashpro')).toBe('ws_workspace_dashpro');
  });
});

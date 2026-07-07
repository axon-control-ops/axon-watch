import { describe, expect, it } from 'vitest';

import { resolveConversationNavigationIntent } from './conversation-intents';

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

  it('switches to grid view', () => {
    expect(resolveConversationNavigationIntent('grid view', WORKSPACES)).toEqual({
      kind: 'switch_center_view',
      centerView: 'grid',
      reply: 'Switching to fleet grid view.',
    });
  });

  it('focuses a workspace by display name', () => {
    expect(resolveConversationNavigationIntent('show me DashPro', WORKSPACES)).toEqual({
      kind: 'focus_workspace',
      workspaceId: 'workspace_dashpro',
      reply: 'Focusing DashPro.',
    });
  });
});

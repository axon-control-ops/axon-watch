import { describe, expect, it } from 'vitest';

import { titleFromWorkspaceId, workspaceIdFromLabel } from './workspace-registration-input';

describe('workspace registration input helpers', () => {
  it('normalizes friendly project names into stable workspace ids', () => {
    expect(workspaceIdFromLabel('MoveIT')).toBe('workspace_move_it');
    expect(workspaceIdFromLabel('Young Eagles Day Care')).toBe('workspace_young_eagles_day_care');
    expect(workspaceIdFromLabel('workspace_existing')).toBe('workspace_existing');
  });

  it('infers readable display names from workspace ids and labels', () => {
    expect(titleFromWorkspaceId('workspace_move_it')).toBe('Move It');
    expect(titleFromWorkspaceId('MoveIT')).toBe('Move IT');
    expect(titleFromWorkspaceId('workspace_tps')).toBe('Tps');
  });
});

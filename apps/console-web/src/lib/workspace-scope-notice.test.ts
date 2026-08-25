import { beforeEach, describe, expect, it } from 'vitest';

import {
  clearWorkspaceScopeNotice,
  isWorkspaceScopePairSuppressed,
  resetWorkspaceScopeStayHere,
  setWorkspaceScopeNotice,
  stayInCurrentWorkspaceScope,
  workspaceScopeNotice,
} from './workspace-scope-notice';

const notice = {
  currentWorkspaceId: 'workspace_dashpro',
  inferredWorkspaceId: 'workspace_young_eagles_day_care',
  inferredLabel: 'Young Eagles Day Care',
  currentLabel: 'DashPro',
  pendingDraft: 'How many children do we have in the Young Eagles preschool tenant?',
};

describe('workspace scope stay-here', () => {
  beforeEach(() => {
    clearWorkspaceScopeNotice();
    resetWorkspaceScopeStayHere();
  });

  it('raises the notice for a fresh workspace pair', () => {
    setWorkspaceScopeNotice(notice);
    expect(workspaceScopeNotice.value).not.toBeNull();
    expect(isWorkspaceScopePairSuppressed(notice.currentWorkspaceId, notice.inferredWorkspaceId))
      .toBe(false);
  });

  it('suppresses that pair after the operator stays here', () => {
    setWorkspaceScopeNotice(notice);
    stayInCurrentWorkspaceScope();

    expect(workspaceScopeNotice.value).toBeNull();
    expect(isWorkspaceScopePairSuppressed(notice.currentWorkspaceId, notice.inferredWorkspaceId))
      .toBe(true);

    // The composer's send guard keys off this: once suppressed the send must
    // fall through instead of aborting, or the composer goes silently dead.
    setWorkspaceScopeNotice(notice);
    expect(workspaceScopeNotice.value).toBeNull();
  });

  it('keeps prompting for a different workspace pair', () => {
    setWorkspaceScopeNotice(notice);
    stayInCurrentWorkspaceScope();

    expect(isWorkspaceScopePairSuppressed('workspace_dashpro', 'workspace_axon_watch')).toBe(false);
    setWorkspaceScopeNotice({ ...notice, inferredWorkspaceId: 'workspace_axon_watch' });
    expect(workspaceScopeNotice.value).not.toBeNull();
  });

  it('plain dismiss does not suppress the pair', () => {
    setWorkspaceScopeNotice(notice);
    clearWorkspaceScopeNotice();

    expect(isWorkspaceScopePairSuppressed(notice.currentWorkspaceId, notice.inferredWorkspaceId))
      .toBe(false);
    setWorkspaceScopeNotice(notice);
    expect(workspaceScopeNotice.value).not.toBeNull();
  });
});

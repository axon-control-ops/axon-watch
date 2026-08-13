import { describe, expect, it } from 'vitest';

import {
  composerWorkspaceScopeBannerCopy,
  inferWorkspaceIdsFromContent,
  resolveComposerWorkspaceScopeMismatch,
} from './composer-workspace-scope';

describe('composer workspace scope', () => {
  it('infers Young Eagles from centre-ops language', () => {
    const draft =
      'School: Young Eagles — link Lesego and add Dimakatso T Mokgabudi to staff visibility.';
    const hits = inferWorkspaceIdsFromContent(draft);
    expect(hits.some((row) => row.workspaceId === 'workspace_young_eagles_day_care')).toBe(true);
  });

  it('flags DashPro composer when draft is Young Eagles ops', () => {
    const mismatch = resolveComposerWorkspaceScopeMismatch(
      'workspace_dashpro',
      'Verify Lesego enrolment in Young Eagles command-centre scripts.',
    );
    expect(mismatch).toMatchObject({
      currentWorkspaceId: 'workspace_dashpro',
      inferredWorkspaceId: 'workspace_young_eagles_day_care',
    });
    expect(composerWorkspaceScopeBannerCopy(mismatch!)).toContain('Young Eagles');
    expect(composerWorkspaceScopeBannerCopy(mismatch!)).toContain('DashPro');
  });

  it('does not flag when draft matches the active workspace', () => {
    expect(
      resolveComposerWorkspaceScopeMismatch(
        'workspace_dashpro',
        'Fix DashPro parent dashboard confirmation popup on Expo OTA.',
      ),
    ).toBeNull();
  });
});

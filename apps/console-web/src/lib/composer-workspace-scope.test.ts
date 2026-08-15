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

  it('does not flag a passing DashPro mention inside dominantly Young-Eagles-scoped text', () => {
    // Regression: an Instructions doc for Young Eagles that merely names a
    // legitimate cross-tenant contact ("consult Dana from Edudash Pro")
    // should not trip the mismatch banner just because the keyword appears.
    const draft =
      '# Instructions\n\n## Goal\n\nUpdate the Young Eagles tenant’s second menu ' +
      'and present an expanded teacher roster table.\n\n## In scope\n\n- Consult ' +
      'Dana from Edudash Pro on the Young Eagles tenant roster requirements.\n\n' +
      '## Constraints\n\n- Preserve existing tenant separation for the Young Eagles tenant.';
    expect(
      resolveComposerWorkspaceScopeMismatch('workspace_young_eagles_day_care', draft),
    ).toBeNull();
  });

  it('still flags when the other workspace is the dominant subject, not a passing mention', () => {
    const draft = 'Ship the DashPro parent dashboard OTA build and notify Dana at DashPro.';
    const mismatch = resolveComposerWorkspaceScopeMismatch(
      'workspace_young_eagles_day_care',
      draft,
    );
    expect(mismatch?.inferredWorkspaceId).toBe('workspace_dashpro');
  });
});

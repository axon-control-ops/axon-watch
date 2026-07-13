import { describe, expect, it } from 'vitest';

import { groupSkillsByWorkspace, skillsSurfaceSummary } from './skills-surface-view';

describe('skills-surface-view', () => {
  it('groups skills by workspace', () => {
    const groups = groupSkillsByWorkspace([
      {
        id: 'a:debug',
        name: 'debug',
        description: 'Debug',
        workspace_id: 'workspace_a',
        workspace_label: 'A',
        path: '.github/skills/debug/SKILL.md',
        slug: 'debug',
      },
      {
        id: 'b:design',
        name: 'design',
        description: 'Design',
        workspace_id: 'workspace_b',
        workspace_label: 'B',
        path: '.github/skills/design/SKILL.md',
        slug: 'design',
      },
    ]);
    expect(groups).toHaveLength(2);
    expect(groups[0]?.skills[0]?.name).toBe('debug');
  });

  it('summarizes empty and populated snapshots', () => {
    expect(skillsSurfaceSummary(null)).toContain('No skills loaded');
    expect(
      skillsSurfaceSummary({ items: [], count: 0, workspaces_scanned: 2 }),
    ).toContain('No SKILL.md');
    expect(
      skillsSurfaceSummary({
        items: [
          {
            id: 'a:debug',
            name: 'debug',
            description: '',
            workspace_id: 'a',
            workspace_label: 'A',
            path: '.github/skills/debug/SKILL.md',
            slug: 'debug',
          },
        ],
        count: 1,
        workspaces_scanned: 1,
      }),
    ).toContain('1 skill');
  });
});

import { describe, expect, it } from 'vitest';

import {
  applySlashSkillToDraft,
  buildSlashPaletteCatalog,
  composerSkillSlugFromPath,
  filterSlashPaletteRows,
  isComposerSkillFilePath,
  listComposerSkillFileTokens,
  prependComposerSkillFileTokens,
  stripComposerSkillFileTokens,
} from './composer-slash-skills-view';

const skills = [
  {
    id: 'ws:super-coder',
    name: 'Super Coder',
    description: 'Full-stack engineering',
    workspace_id: 'workspace_axon_watch',
    workspace_label: 'Axon Watch',
    path: '.github/skills/super-coder/SKILL.md',
    slug: 'super-coder',
  },
  {
    id: 'ws:debug',
    name: 'Debug',
    description: 'Generic debugging',
    workspace_id: 'workspace_other',
    workspace_label: 'Other',
    path: '.github/skills/debug/SKILL.md',
    slug: 'debug',
  },
];

describe('composer-slash-skills-view', () => {
  it('builds skill and mode rows', () => {
    const rows = buildSlashPaletteCatalog(skills, 'workspace_axon_watch');
    expect(rows.some((row) => row.command === '/super-coder')).toBe(true);
    expect(rows.some((row) => row.command === '/agent')).toBe(true);
  });

  it('filters by query prefix', () => {
    const rows = filterSlashPaletteRows(buildSlashPaletteCatalog(skills), 'super');
    expect(rows).toHaveLength(1);
    expect(rows[0]?.command).toBe('/super-coder');
  });

  it('applies slash skill without dumping raw @file into the draft', () => {
    const result = applySlashSkillToDraft(
      '/super-coder fix the dock',
      { start: 0, end: 13 },
      '.github/skills/super-coder/SKILL.md',
    );
    expect(result.next).toBe('fix the dock');
    expect(result.skillPath).toBe('.github/skills/super-coder/SKILL.md');
  });

  it('parses, strips, and prepends skill file tokens for Cursor-style chips', () => {
    expect(isComposerSkillFilePath('.github/skills/super-coder/SKILL.md')).toBe(true);
    expect(composerSkillSlugFromPath('.github/skills/super-coder/SKILL.md')).toBe(
      'super-coder',
    );

    const draft =
      '@file:.github/skills/super-coder/SKILL.md\n@file:README.md\nfix the dock';
    expect(listComposerSkillFileTokens(draft)).toEqual([
      {
        path: '.github/skills/super-coder/SKILL.md',
        slug: 'super-coder',
        label: 'super-coder',
        token: '@file:.github/skills/super-coder/SKILL.md',
      },
    ]);
    expect(stripComposerSkillFileTokens(draft)).toBe('@file:README.md\nfix the dock');
    expect(
      prependComposerSkillFileTokens('fix the dock', [
        '.github/skills/super-coder/SKILL.md',
      ]),
    ).toBe('@file:.github/skills/super-coder/SKILL.md\nfix the dock');
  });
});

import { describe, expect, it } from 'vitest';

import {
  applySlashSkillToDraft,
  buildSlashPaletteCatalog,
  composerSkillSlugFromPath,
  filterSlashPaletteRows,
  isComposerSkillFilePath,
  listComposerSkillFileTokens,
  longestCommonSlashPrefix,
  prependComposerSkillFileTokens,
  resolveSlashTabAction,
  SLASH_STATUS_PROMPT,
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
  it('lists modes before skills so / opens with Ask/Agent first', () => {
    const rows = buildSlashPaletteCatalog(skills, 'workspace_axon_watch');
    expect(rows[0]?.command).toBe('/ask');
    expect(rows.some((row) => row.command === '/status')).toBe(true);
    expect(rows.some((row) => row.command === '/super-coder')).toBe(true);
    expect(rows.findIndex((row) => row.command === '/ask')).toBeLessThan(
      rows.findIndex((row) => row.command === '/super-coder'),
    );
  });

  it('clarifies Lead Ask vs Agent fan-out copy', () => {
    const rows = buildSlashPaletteCatalog(skills, 'workspace_axon_watch', {
      leadThread: true,
    });
    expect(rows.find((row) => row.command === '/ask')?.detail).toMatch(/no specialist/i);
    expect(rows.find((row) => row.command === '/agent')?.detail).toMatch(/fan out/i);
  });

  it('ranks command prefix matches ahead of weak includes', () => {
    const rows = filterSlashPaletteRows(buildSlashPaletteCatalog(skills), 'ask');
    expect(rows[0]?.command).toBe('/ask');
  });

  it('filters skill query by prefix', () => {
    const rows = filterSlashPaletteRows(buildSlashPaletteCatalog(skills), 'super');
    expect(rows).toHaveLength(1);
    expect(rows[0]?.command).toBe('/super-coder');
  });

  it('computes longest common slash prefix for Tab', () => {
    expect(longestCommonSlashPrefix(['/ask', '/agent'])).toBe('a');
    expect(longestCommonSlashPrefix(['/status', '/status'])).toBe('status');
    expect(longestCommonSlashPrefix(['/ask', '/plan'])).toBe('');
  });

  it('resolves Tab to complete before apply', () => {
    expect(
      resolveSlashTabAction({
        query: '',
        selectedCommand: '/ask',
        filteredCommands: ['/ask', '/agent'],
      }),
    ).toBe('complete-common');
    expect(
      resolveSlashTabAction({
        query: 'a',
        selectedCommand: '/ask',
        filteredCommands: ['/ask', '/agent'],
      }),
    ).toBe('complete-selected');
    expect(
      resolveSlashTabAction({
        query: 'as',
        selectedCommand: '/ask',
        filteredCommands: ['/ask'],
      }),
    ).toBe('complete-selected');
    expect(
      resolveSlashTabAction({
        query: 'ask',
        selectedCommand: '/ask',
        filteredCommands: ['/ask'],
      }),
    ).toBe('apply');
  });

  it('keeps status prompt constant for /status', () => {
    expect(SLASH_STATUS_PROMPT).toMatch(/status of everything/i);
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

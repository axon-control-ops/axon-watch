import type { OperatorSkillRecord } from '../api/skills-api';

export type SlashModeKey = 'agent' | 'plan' | 'ask' | 'debug' | 'kairo';

export type SlashPaletteRow = {
  id: string;
  command: string;
  label: string;
  detail: string;
  kind: 'skill' | 'mode' | 'command';
  skillPath?: string;
  skillSlug?: string;
  mode?: SlashModeKey;
};

const MODE_COMMAND_ROWS: SlashPaletteRow[] = [
  {
    id: 'mode:ask',
    command: '/ask',
    label: 'Ask',
    detail: 'Switch composer to Ask mode',
    kind: 'mode',
    mode: 'ask',
  },
  {
    id: 'mode:plan',
    command: '/plan',
    label: 'Plan',
    detail: 'Switch composer to Plan mode',
    kind: 'mode',
    mode: 'plan',
  },
  {
    id: 'mode:agent',
    command: '/agent',
    label: 'Agent',
    detail: 'Switch composer to Agent mode',
    kind: 'mode',
    mode: 'agent',
  },
  {
    id: 'mode:debug',
    command: '/debug',
    label: 'Debug',
    detail: 'Switch composer to Debug mode',
    kind: 'mode',
    mode: 'debug',
  },
  {
    id: 'mode:kairo',
    command: '/kairo',
    label: 'Kairo',
    detail: 'Switch composer to Kairo voice mode',
    kind: 'mode',
    mode: 'kairo',
  },
];

const UTILITY_COMMAND_ROWS: SlashPaletteRow[] = [
  {
    id: 'cmd:help',
    command: '/help',
    label: 'Help',
    detail: 'List slash skills and mode commands',
    kind: 'command',
  },
];

export function skillToSlashRow(skill: OperatorSkillRecord): SlashPaletteRow {
  return {
    id: `skill:${skill.id}`,
    command: `/${skill.slug}`,
    label: skill.name,
    detail: skill.description || `${skill.workspace_label} skill`,
    kind: 'skill',
    skillPath: skill.path,
    skillSlug: skill.slug,
  };
}

export function buildSlashPaletteCatalog(
  skills: OperatorSkillRecord[],
  workspaceId?: string | null,
): SlashPaletteRow[] {
  const scoped = workspaceId
    ? skills.filter((skill) => skill.workspace_id === workspaceId)
    : skills;
  const skillRows = (scoped.length ? scoped : skills).map(skillToSlashRow);
  return [...skillRows, ...MODE_COMMAND_ROWS, ...UTILITY_COMMAND_ROWS];
}

export function filterSlashPaletteRows(
  rows: SlashPaletteRow[],
  query: string,
  limit = 10,
): SlashPaletteRow[] {
  const normalized = query.trim().toLowerCase().replace(/^\//, '');
  if (!normalized) {
    return rows.slice(0, limit);
  }
  const filtered = rows.filter((row) => {
    const haystack = `${row.command} ${row.label} ${row.detail} ${row.skillSlug ?? ''}`.toLowerCase();
    return row.command.slice(1).startsWith(normalized) || haystack.includes(normalized);
  });
  return filtered.slice(0, limit);
}

/** True when a path points at a Cursor-style `SKILL.md` under a skills folder. */
export function isComposerSkillFilePath(path: string): boolean {
  const normalized = path.trim().replace(/\\/g, '/');
  return /(^|\/)skills\/[^/]+\/SKILL\.md$/i.test(normalized);
}

/** Skill folder slug from `.github/skills/super-coder/SKILL.md` → `super-coder`. */
export function composerSkillSlugFromPath(path: string): string {
  const normalized = path.trim().replace(/\\/g, '/');
  const match = normalized.match(/(?:^|\/)skills\/([^/]+)\/SKILL\.md$/i);
  return match?.[1]?.trim() || 'skill';
}

export type ComposerSkillFileToken = {
  path: string;
  slug: string;
  label: string;
  token: string;
};

const SKILL_FILE_TOKEN_RE =
  /(^|\s)@file:([^\s]+skills\/[^/\s]+\/SKILL\.md)(?=\s|$)/gim;

/** List unique `@file:…/skills/<slug>/SKILL.md` tokens in a composer draft. */
export function listComposerSkillFileTokens(draft: string): ComposerSkillFileToken[] {
  const found: ComposerSkillFileToken[] = [];
  const seen = new Set<string>();
  const text = draft ?? '';
  for (const match of text.matchAll(SKILL_FILE_TOKEN_RE)) {
    const path = String(match[2] || '').trim();
    if (!path || seen.has(path) || !isComposerSkillFilePath(path)) {
      continue;
    }
    seen.add(path);
    const slug = composerSkillSlugFromPath(path);
    found.push({
      path,
      slug,
      label: slug,
      token: `@file:${path}`,
    });
  }
  return found;
}

/** Remove skill `@file:` tokens from the visible composer draft. */
export function stripComposerSkillFileTokens(draft: string): string {
  return (draft ?? '')
    .replace(SKILL_FILE_TOKEN_RE, '$1')
    .replace(/[ \t]+\n/g, '\n')
    .replace(/\n{3,}/g, '\n\n')
    .replace(/[ ]{2,}/g, ' ')
    .trim();
}

export function removeComposerSkillFileToken(draft: string, skillPath: string): string {
  const fileToken = `@file:${skillPath}`;
  const escaped = fileToken.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  return (draft ?? '')
    .replace(new RegExp(`(^|\\s)${escaped}(?=\\s|$)`, 'gm'), '$1')
    .replace(/[ \t]+\n/g, '\n')
    .replace(/\n{3,}/g, '\n\n')
    .replace(/[ ]{2,}/g, ' ')
    .trim();
}

/** Re-attach skill file tokens at the top of the draft for submit/steer. */
export function prependComposerSkillFileTokens(
  draft: string,
  skillPaths: readonly string[],
): string {
  const uniquePaths = [
    ...new Set(
      skillPaths
        .map((path) => path.trim())
        .filter((path) => path && isComposerSkillFilePath(path)),
    ),
  ];
  if (!uniquePaths.length) {
    return (draft ?? '').trim();
  }
  const body = stripComposerSkillFileTokens(draft);
  const header = uniquePaths.map((path) => `@file:${path}`).join('\n');
  return body ? `${header}\n${body}` : header;
}

/**
 * Apply a skill slash command: leave trailing prompt args in the draft.
 * The `@file:SKILL.md` attachment is tracked as a Cursor-style chip (not raw text).
 */
export function applySlashSkillToDraft(
  draft: string,
  token: { start: number; end: number },
  skillPath: string,
): { next: string; caret: number; skillPath: string } {
  const remainder = draft.slice(token.end).replace(/^\s+/, '');
  const next = `${draft.slice(0, token.start)}${remainder}`.replace(/[ ]{2,}/g, ' ').trimStart();
  return { next, caret: Math.min(token.start, next.length), skillPath };
}

export function slashHelpText(rows: SlashPaletteRow[]): string {
  return [
    'Slash commands:',
    ...rows.map((row) => `- \`${row.command}\` ${row.detail}`),
  ].join('\n');
}

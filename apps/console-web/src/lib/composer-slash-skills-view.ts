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

/** Apply a skill: attach `@file:SKILL.md` and leave any trailing prompt args. */
export function applySlashSkillToDraft(
  draft: string,
  token: { start: number; end: number },
  skillPath: string,
): { next: string; caret: number } {
  const fileToken = `@file:${skillPath}`;
  const remainder = draft.slice(token.end).replace(/^\s+/, '');
  const withoutToken = `${draft.slice(0, token.start)}${remainder}`.trim();
  const hasFile = new RegExp(
    `(^|\\s)${fileToken.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}(?=\\s|$)`,
    'm',
  ).test(withoutToken);
  const next = hasFile
    ? withoutToken
    : withoutToken
      ? `${fileToken}\n${withoutToken}`
      : fileToken;
  return { next, caret: next.length };
}

export function slashHelpText(rows: SlashPaletteRow[]): string {
  return [
    'Slash commands:',
    ...rows.map((row) => `- \`${row.command}\` ${row.detail}`),
  ].join('\n');
}

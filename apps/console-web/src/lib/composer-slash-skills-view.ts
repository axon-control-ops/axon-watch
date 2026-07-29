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

export type SlashPaletteContext = {
  /** Active IDE thread is a Lead employee — clarify Ask vs Agent fan-out. */
  leadThread?: boolean;
};

const MODE_COMMAND_ROWS: SlashPaletteRow[] = [
  {
    id: 'mode:ask',
    command: '/ask',
    label: 'Ask',
    detail: 'Answer-only mode — no edits, no specialist fan-out',
    kind: 'mode',
    mode: 'ask',
  },
  {
    id: 'mode:plan',
    command: '/plan',
    label: 'Plan',
    detail: 'Outline an approach before implementing',
    kind: 'mode',
    mode: 'plan',
  },
  {
    id: 'mode:agent',
    command: '/agent',
    label: 'Agent',
    detail: 'Full Access implement mode',
    kind: 'mode',
    mode: 'agent',
  },
  {
    id: 'mode:debug',
    command: '/debug',
    label: 'Debug',
    detail: 'Runtime evidence / debug loop',
    kind: 'mode',
    mode: 'debug',
  },
  {
    id: 'mode:kairo',
    command: '/kairo',
    label: 'Kairo',
    detail: 'Voice-first Kairo mode',
    kind: 'mode',
    mode: 'kairo',
  },
];

const UTILITY_COMMAND_ROWS: SlashPaletteRow[] = [
  {
    id: 'cmd:status',
    command: '/status',
    label: 'Status',
    detail: 'Ask for a fleet status brief (Ask mode — no fan-out)',
    kind: 'command',
  },
  {
    id: 'cmd:help',
    command: '/help',
    label: 'Help',
    detail: 'List slash skills and mode commands',
    kind: 'command',
  },
];

function modeRowsForContext(context?: SlashPaletteContext | null): SlashPaletteRow[] {
  if (!context?.leadThread) {
    return MODE_COMMAND_ROWS;
  }
  return MODE_COMMAND_ROWS.map((row) => {
    if (row.mode === 'ask') {
      return {
        ...row,
        detail: 'Ask Lead — answer only, no specialist tasks',
      };
    }
    if (row.mode === 'agent') {
      return {
        ...row,
        detail: 'Lead Agent — implement asks fan out to specialists',
      };
    }
    return row;
  });
}

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
  context?: SlashPaletteContext | null,
): SlashPaletteRow[] {
  const scoped = workspaceId
    ? skills.filter((skill) => skill.workspace_id === workspaceId)
    : skills;
  const skillRows = (scoped.length ? scoped : skills).map(skillToSlashRow);
  // Modes/utilities first so `/` opens with Ask/Agent/Status before skill spam.
  return [...modeRowsForContext(context), ...UTILITY_COMMAND_ROWS, ...skillRows];
}

function slashMatchScore(row: SlashPaletteRow, normalized: string): number {
  const commandBody = row.command.slice(1).toLowerCase();
  const label = row.label.toLowerCase();
  const slug = (row.skillSlug ?? '').toLowerCase();
  if (commandBody === normalized || label === normalized || slug === normalized) {
    return 400;
  }
  if (commandBody.startsWith(normalized)) {
    return 300 - Math.min(commandBody.length, 99);
  }
  if (label.startsWith(normalized) || slug.startsWith(normalized)) {
    return 200;
  }
  const haystack = `${row.command} ${row.label} ${row.detail} ${slug}`.toLowerCase();
  if (haystack.includes(normalized)) {
    return 100;
  }
  return 0;
}

function kindRank(kind: SlashPaletteRow['kind']): number {
  if (kind === 'mode') {
    return 3;
  }
  if (kind === 'command') {
    return 2;
  }
  return 1;
}

/** Ranked filter: exact/prefix modes first, then commands, then skills. */
export function filterSlashPaletteRows(
  rows: SlashPaletteRow[],
  query: string,
  limit = 12,
): SlashPaletteRow[] {
  const normalized = query.trim().toLowerCase().replace(/^\//, '');
  if (!normalized) {
    return rows.slice(0, limit);
  }
  return rows
    .map((row) => ({ row, score: slashMatchScore(row, normalized) }))
    .filter((entry) => entry.score > 0)
    .sort((a, b) => {
      if (b.score !== a.score) {
        return b.score - a.score;
      }
      const kindDelta = kindRank(b.row.kind) - kindRank(a.row.kind);
      if (kindDelta !== 0) {
        return kindDelta;
      }
      return a.row.command.localeCompare(b.row.command);
    })
    .slice(0, limit)
    .map((entry) => entry.row);
}

/** Shared command-body prefix across filtered rows (without leading `/`). */
export function longestCommonSlashPrefix(commands: readonly string[]): string {
  const bodies = commands
    .map((command) => command.trim().replace(/^\//, '').toLowerCase())
    .filter(Boolean);
  if (!bodies.length) {
    return '';
  }
  let prefix = bodies[0] ?? '';
  for (const body of bodies.slice(1)) {
    let i = 0;
    while (i < prefix.length && i < body.length && prefix[i] === body[i]) {
      i += 1;
    }
    prefix = prefix.slice(0, i);
    if (!prefix) {
      return '';
    }
  }
  return prefix;
}

export type SlashTabAction = 'complete-common' | 'complete-selected' | 'apply';

/**
 * Decide Tab behavior for an open slash palette.
 * Tab completes text first; only applies when the selected command is already typed.
 */
export function resolveSlashTabAction(input: {
  query: string;
  selectedCommand: string;
  filteredCommands: readonly string[];
}): SlashTabAction {
  const query = input.query.trim().replace(/^\//, '').toLowerCase();
  const selected = input.selectedCommand.trim().replace(/^\//, '').toLowerCase();
  if (!selected) {
    return 'apply';
  }
  const common = longestCommonSlashPrefix(input.filteredCommands);
  if (
    input.filteredCommands.length > 1 &&
    common.length > query.length &&
    common !== selected
  ) {
    return 'complete-common';
  }
  if (query === selected) {
    return 'apply';
  }
  return 'complete-selected';
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

export const SLASH_STATUS_PROMPT = 'Give me a status of everything.';

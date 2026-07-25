import type { OperatorSkillRecord } from '../api/skills-api';

export type EmployeeSkillHint = {
  slug: string;
  name: string;
  command: string;
  path: string;
};

const ROLE_SKILL_KEYWORDS: Record<string, readonly string[]> = {
  frontend: ['frontend', 'ui', 'ux', 'vue', 'css', 'shell', 'component', 'design', 'web'],
  backend: ['backend', 'api', 'server', 'migration', 'database', 'debug', 'python'],
  integrations: ['integration', 'connector', 'sdk', 'github', 'workflow', 'ci', 'deploy'],
  watcher: ['watch', 'monitor', 'alert', 'signal', 'sentry', 'debug', 'inbox'],
  lead: ['architect', 'plan', 'review', 'split', 'lead', 'babysit'],
  overview_agent: ['architect', 'overview', 'plan'],
  workspace_agent: ['coder', 'debug', 'implement'],
};

export function scoreSkillForEmployeeRole(
  skill: OperatorSkillRecord,
  role: string | null | undefined,
): number {
  const keywords = ROLE_SKILL_KEYWORDS[(role ?? '').trim().toLowerCase()] ?? [];
  if (!keywords.length) {
    return 0;
  }
  const haystack = `${skill.slug} ${skill.name} ${skill.description}`.toLowerCase();
  let score = 0;
  for (const keyword of keywords) {
    if (haystack.includes(keyword)) {
      score += 1;
    }
  }
  return score;
}

export function rankSkillsForEmployeeRole(
  skills: readonly OperatorSkillRecord[],
  role: string | null | undefined,
  workspaceId?: string | null,
  limit = 4,
): EmployeeSkillHint[] {
  const scoped = workspaceId
    ? skills.filter((skill) => skill.workspace_id === workspaceId)
    : skills;
  const pool = scoped.length ? scoped : skills;

  return [...pool]
    .map((skill) => ({ skill, score: scoreSkillForEmployeeRole(skill, role) }))
    .filter((row) => row.score > 0)
    .sort(
      (left, right) =>
        right.score - left.score ||
        left.skill.name.localeCompare(right.skill.name, undefined, { sensitivity: 'base' }),
    )
    .slice(0, limit)
    .map(({ skill }) => ({
      slug: skill.slug,
      name: skill.name,
      command: `/${skill.slug}`,
      path: skill.path,
    }));
}

export function employeeSkillComposerDraft(skill: EmployeeSkillHint): string {
  return `${skill.command} `;
}

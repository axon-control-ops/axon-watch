import type { OperatorSkillRecord, OperatorSkillsSnapshot } from '../api/skills-api';

export function groupSkillsByWorkspace(
  items: OperatorSkillRecord[],
): Array<{ workspaceLabel: string; workspaceId: string; skills: OperatorSkillRecord[] }> {
  const groups = new Map<
    string,
    { workspaceLabel: string; workspaceId: string; skills: OperatorSkillRecord[] }
  >();

  for (const skill of items) {
    const existing = groups.get(skill.workspace_id);
    if (existing) {
      existing.skills.push(skill);
      continue;
    }
    groups.set(skill.workspace_id, {
      workspaceId: skill.workspace_id,
      workspaceLabel: skill.workspace_label,
      skills: [skill],
    });
  }

  return Array.from(groups.values());
}

export function skillsSurfaceSummary(snapshot: OperatorSkillsSnapshot | null): string {
  if (!snapshot) {
    return 'No skills loaded yet.';
  }
  if (snapshot.count === 0) {
    return `No SKILL.md files found under .github/skills in ${snapshot.workspaces_scanned} bound workspace(s).`;
  }
  return `${snapshot.count} skill(s) across ${snapshot.workspaces_scanned} bound workspace(s).`;
}

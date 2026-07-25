import { describe, expect, it } from 'vitest';

import type { OperatorSkillRecord } from '../api/skills-api';
import {
  employeeSkillComposerDraft,
  rankSkillsForEmployeeRole,
  scoreSkillForEmployeeRole,
} from './employee-skill-map';

const skills: OperatorSkillRecord[] = [
  {
    id: '1',
    name: 'Axon Frontend',
    description: 'Console UI and shell polish',
    workspace_id: 'workspace_axon_watch',
    workspace_label: 'Axon Watch',
    path: '.github/skills/axon-frontend/SKILL.md',
    slug: 'axon-frontend',
  },
  {
    id: '2',
    name: 'Super Coder',
    description: 'Full-stack engineering',
    workspace_id: 'workspace_axon_local',
    workspace_label: 'Axon Local',
    path: '.github/skills/super-coder/SKILL.md',
    slug: 'super-coder',
  },
  {
    id: '3',
    name: 'Debug',
    description: 'Generic debugging playbook',
    workspace_id: 'workspace_axon_watch',
    workspace_label: 'Axon Watch',
    path: '.github/skills/debug/SKILL.md',
    slug: 'debug',
  },
];

describe('employee-skill-map', () => {
  it('scores frontend skills higher for frontend roles', () => {
    expect(scoreSkillForEmployeeRole(skills[0], 'frontend')).toBeGreaterThan(0);
    expect(scoreSkillForEmployeeRole(skills[1], 'frontend')).toBe(0);
  });

  it('ranks role-aligned skills for an employee', () => {
    const ranked = rankSkillsForEmployeeRole(skills, 'frontend', 'workspace_axon_watch');
    expect(ranked.map((row) => row.slug)).toEqual(['axon-frontend']);
  });

  it('builds composer drafts from skill hints', () => {
    expect(employeeSkillComposerDraft(rankedSkill())).toBe('/axon-frontend ');
  });
});

function rankedSkill() {
  return rankSkillsForEmployeeRole(skills, 'frontend', 'workspace_axon_watch')[0]!;
}

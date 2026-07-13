import { fetchJson } from './client';

export type OperatorSkillRecord = {
  id: string;
  name: string;
  description: string;
  workspace_id: string;
  workspace_label: string;
  path: string;
  slug: string;
};

export type OperatorSkillsSnapshot = {
  items: OperatorSkillRecord[];
  count: number;
  workspaces_scanned: number;
};

export async function fetchSkillsSnapshot(): Promise<OperatorSkillsSnapshot> {
  return fetchJson<OperatorSkillsSnapshot>(
    '/api/skills',
    {},
    'skills request failed',
  );
}

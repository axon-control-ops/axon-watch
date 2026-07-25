import type { WorkspaceAgentRecord } from '../../contracts/canonical';

const STATUS_MAX = 40;

/** Compact picker subtitle — never surface transcript/thought prose as meta. */
export function workspaceAgentLabel(agent: WorkspaceAgentRecord | null | undefined): string {
  if (!agent?.agent_name?.trim()) {
    return '';
  }
  const name = agent.agent_name.trim();
  const status = agent.status?.trim();
  if (!status || status === 'idle') {
    return name;
  }
  const compact = status.replace(/_/g, ' ');
  if (
    compact.length > STATUS_MAX ||
    /\bthought\b/i.test(compact) ||
    /\s{2,}/.test(compact) ||
    compact.includes('—') ||
    compact.includes('.')
  ) {
    return name;
  }
  return `${name} · ${compact}`;
}

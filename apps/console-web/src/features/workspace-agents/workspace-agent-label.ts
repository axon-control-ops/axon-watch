import type { WorkspaceAgentRecord } from '../../contracts/canonical';

export function workspaceAgentLabel(agent: WorkspaceAgentRecord | null | undefined): string {
  if (!agent?.agent_name?.trim()) {
    return '';
  }
  const status = agent.status?.trim();
  if (!status || status === 'idle') {
    return agent.agent_name.trim();
  }
  return `${agent.agent_name.trim()} · ${status.replace(/_/g, ' ')}`;
}

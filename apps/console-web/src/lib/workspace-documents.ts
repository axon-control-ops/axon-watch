import type { InboxItem, RunRecord, RuntimeSummary, WorkspaceRecord } from '../contracts/canonical';

export interface WorkspaceDocumentDescriptor {
  id: string;
  title: string;
  language: 'markdown' | 'json';
  value: string;
  description: string;
}

interface BuildWorkspaceDocumentsInput {
  workspace: WorkspaceRecord | null;
  runs: RunRecord[];
  runtimeSummary: RuntimeSummary | null;
  primaryInboxItem: InboxItem | null;
}

function prettyJson(value: unknown): string {
  return `${JSON.stringify(value, null, 2)}\n`;
}

export function buildWorkspaceDocuments({
  workspace,
  runs,
  runtimeSummary,
  primaryInboxItem,
}: BuildWorkspaceDocumentsInput): WorkspaceDocumentDescriptor[] {
  const workspaceId = workspace?.workspace_id ?? 'workspace_unbound';
  const workspaceRuns = runs.filter((run) => run.workspace_id === workspace?.workspace_id);
  const activeWorkspaceRun =
    workspaceRuns.find((run) => run.phase !== 'completed' && run.phase !== 'failed' && run.phase !== 'cancelled') ??
    workspaceRuns[0] ??
    null;

  const overview = [
    `# Workspace ${workspaceId}`,
    '',
    `- active run count: ${workspaceRuns.length}`,
    `- active run phase: ${activeWorkspaceRun?.phase ?? 'none'}`,
    `- active run status: ${activeWorkspaceRun?.status ?? 'none'}`,
    `- watch connected: ${runtimeSummary?.watch.connected ? 'yes' : 'no'}`,
    `- top signal: ${primaryInboxItem?.signal_id ?? 'none'}`,
    '',
    'This editor surface is now bound to canonical workspace and runtime DTOs.',
  ].join('\n');

  return [
    {
      id: 'workspace-overview',
      title: 'Workspace Overview',
      language: 'markdown',
      value: `${overview}\n`,
      description: 'Workspace-oriented summary assembled from canonical DTOs.',
    },
    {
      id: 'workspace-run-record',
      title: 'Run Record',
      language: 'json',
      value: prettyJson(activeWorkspaceRun ?? { workspace_id: workspaceId, run: null }),
      description: 'The primary run record for the selected workspace.',
    },
    {
      id: 'workspace-runtime-summary',
      title: 'Runtime Summary',
      language: 'json',
      value: prettyJson(runtimeSummary ?? { runtime_summary: null }),
      description: 'The boot-safe runtime summary payload currently loaded in the shell.',
    },
    {
      id: 'workspace-top-signal',
      title: 'Top Signal',
      language: 'json',
      value: prettyJson(primaryInboxItem ?? { signal: null }),
      description: 'The current top-ranked inbox item visible to the shell.',
    },
  ];
}

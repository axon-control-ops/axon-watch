export type WorkbenchProblemShellSlice = {
  fileSaveError: string | null;
  workspaceFilesError: string | null;
  commandMutationError: string | null;
  runMutationError: string | null;
  runtimeSummaryError: string | null;
  briefingError: string | null;
  runsError: string | null;
  inboxError: string | null;
};

export function buildWorkbenchProblemItems(shell: WorkbenchProblemShellSlice): string[] {
  const items: string[] = [];
  if (shell.fileSaveError) items.push(`Save failed: ${shell.fileSaveError}`);
  if (shell.workspaceFilesError) items.push(`Workspace files: ${shell.workspaceFilesError}`);
  if (shell.commandMutationError) items.push(`Command: ${shell.commandMutationError}`);
  if (shell.runMutationError) items.push(`Run: ${shell.runMutationError}`);
  if (shell.runtimeSummaryError) items.push(`Runtime summary: ${shell.runtimeSummaryError}`);
  if (shell.briefingError) items.push(`Briefing: ${shell.briefingError}`);
  if (shell.runsError) items.push(`Runs: ${shell.runsError}`);
  if (shell.inboxError) items.push(`Inbox: ${shell.inboxError}`);
  return items;
}

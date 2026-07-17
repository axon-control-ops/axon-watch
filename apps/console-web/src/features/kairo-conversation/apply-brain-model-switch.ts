import type { CursorCatalogRow } from '../../lib/cursor-catalog-view';
import { isCursorAutoModel } from '../../lib/cursor-catalog-view';
import type { useShellStore } from '../../stores/shell';

type ShellStore = ReturnType<typeof useShellStore>;

/** Route orb/brain model picks through Cursor CLI runtime when possible. */
export function ensureCursorRuntimeForBrainModel(shell: ShellStore): void {
  const status = shell.runtimeStatus;
  if (!status) {
    return;
  }

  const records = [...status.local, ...status.cloud];
  const current = records.find((record) => record.id === shell.selectedRuntimeTargetId);
  if (current?.family === 'cursor') {
    return;
  }

  const cursorRuntime =
    records.find((record) => record.family === 'cursor' && record.target_type !== 'cloud') ??
    records.find((record) => record.family === 'cursor');
  if (cursorRuntime) {
    shell.setSelectedRuntimeTarget(cursorRuntime.id);
  }
}

export function applyBrainModelSwitch(
  shell: ShellStore,
  input: { modelId: string; rows: CursorCatalogRow[] },
): boolean {
  if (!shell.currentWorkspace?.workspace_id) {
    return false;
  }

  if (!input.modelId || isCursorAutoModel(input.modelId)) {
    shell.setSelectedComposerModel('auto');
    return true;
  }

  ensureCursorRuntimeForBrainModel(shell);
  shell.setSelectedComposerModel(input.modelId);
  return true;
}

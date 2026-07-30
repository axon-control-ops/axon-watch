import type { CursorCatalogRow } from '../../lib/cursor-catalog-view';
import { isCursorAutoModel } from '../../lib/cursor-catalog-view';
import {
  DEFAULT_VAXON_MODEL_ID,
  VAXON_MODEL_OPTIONS,
} from '../../lib/operator-presence-settings';
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

/**
 * Apply a spoken "change VAXON's brain" intent to the operator-global VAXON
 * model setting — never to the workspace Agent Dock composer preference.
 */
export function applyBrainModelSwitch(
  shell: ShellStore,
  input: { modelId: string; rows: CursorCatalogRow[] },
): boolean {
  void input.rows;
  const allowlist = new Set<string>(VAXON_MODEL_OPTIONS.map((row) => row.id));
  const nextId =
    !input.modelId || isCursorAutoModel(input.modelId)
      ? DEFAULT_VAXON_MODEL_ID
      : allowlist.has(input.modelId)
        ? input.modelId
        : /^[a-z0-9][a-z0-9._-]{1,118}$/i.test(input.modelId)
          ? input.modelId.slice(0, 120)
          : DEFAULT_VAXON_MODEL_ID;

  ensureCursorRuntimeForBrainModel(shell);
  void shell.saveOperatorPresenceSettingsPatch({ vaxon_model_id: nextId });
  return true;
}

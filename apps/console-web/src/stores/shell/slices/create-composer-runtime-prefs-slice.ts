import { computed, type ComputedRef, type Ref } from 'vue';

import type {
  CodexRuntimeStatusSnapshot,
  CursorRuntimeStatusSnapshot,
  RuntimeStatusSnapshot,
} from '../../../api/control-plane';
import {
  buildCursorCatalogRows,
  cursorComposerRuntimeLabel,
  resolveCursorComposerModel,
  type CursorCatalogRow,
} from '../../../lib/cursor-catalog-view';
import { buildCodexCatalogRows, codexModelLabel } from '../../../lib/codex-catalog-view';
import {
  readComposerRuntimePrefs,
  writeComposerRuntimePrefs,
} from '../../../lib/composer-runtime-prefs';
import {
  readCursorPickerVisibleModelIds,
  toggleCursorPickerVisibleModel as toggleCursorPickerVisibleModelPref,
} from '../../../lib/cursor-picker-prefs';
import { saveWorkspaceComposerPrefs } from '../../../api/workspace-api';
import type { WorkspaceRecord } from '../../../contracts/canonical';

interface CreateComposerRuntimePrefsSliceInput {
  currentWorkspace: Ref<WorkspaceRecord | null>;
  runtimeStatus: Ref<RuntimeStatusSnapshot | null>;
  cursorRuntimeStatus: Ref<CursorRuntimeStatusSnapshot | null>;
  codexRuntimeStatus: Ref<CodexRuntimeStatusSnapshot | null>;
  composerRuntimePrefsRevision: Ref<number>;
  cursorPickerVisibleRevision: Ref<number>;
}

export function createComposerRuntimePrefsSlice(input: CreateComposerRuntimePrefsSliceInput) {
  const composerRuntimePrefs = computed(() => {
    input.composerRuntimePrefsRevision.value;
    return readComposerRuntimePrefs(input.currentWorkspace.value?.workspace_id ?? null);
  });

  const selectedRuntimeTargetId = computed(() => {
    const preferred = composerRuntimePrefs.value.runtime_target?.trim();
    if (preferred) {
      return preferred;
    }
    return input.runtimeStatus.value?.default_runtime ?? '';
  });

  const cursorCatalogRows: ComputedRef<CursorCatalogRow[]> = computed(() =>
    buildCursorCatalogRows(input.cursorRuntimeStatus.value),
  );
  const codexCatalogRows: ComputedRef<CursorCatalogRow[]> = computed(() =>
    buildCodexCatalogRows(input.codexRuntimeStatus.value),
  );

  const selectedComposerModel = computed(() => {
    const workspaceId = input.currentWorkspace.value?.workspace_id ?? null;
    if (!workspaceId) {
      return 'composer-2.5-fast';
    }
    const prefs = composerRuntimePrefs.value;
    const target = selectedRuntimeTargetId.value;
    const targetRecord = [
      ...(input.runtimeStatus.value?.local ?? []),
      ...(input.runtimeStatus.value?.cloud ?? []),
    ].find((record) => record.id === target);
    const family = targetRecord?.family ?? 'cursor';
    if (family === 'codex') {
      return prefs.codex_cli_model?.trim() || 'auto';
    }
    if (family === 'claude') {
      return prefs.claude_cli_model?.trim() || 'auto';
    }
    const stored = prefs.cursor_cli_model?.trim();
    if (!stored || stored === 'auto') {
      return stored || 'auto';
    }
    return resolveCursorComposerModel(stored, cursorCatalogRows.value);
  });

  const cursorPickerVisibleModelIds = computed(() => {
    input.cursorPickerVisibleRevision.value;
    return readCursorPickerVisibleModelIds();
  });

  const composerRuntimeLabel = computed(() => {
    const target = [
      ...(input.runtimeStatus.value?.local ?? []),
      ...(input.runtimeStatus.value?.cloud ?? []),
    ].find((record) => record.id === selectedRuntimeTargetId.value);
    const scope = target?.target_type === 'cloud' ? 'cloud' : 'local';
    const family = target?.family ?? 'runtime';
    if (family === 'cursor') {
      return cursorComposerRuntimeLabel({
        family,
        scope,
        modelId: selectedComposerModel.value,
        rows: cursorCatalogRows.value,
      });
    }
    const model = selectedComposerModel.value;
    const modelLabel = family === 'codex'
      ? codexModelLabel(model, codexCatalogRows.value)
      : model === 'auto' ? 'Auto' : model;
    return `${family} ${scope} · ${modelLabel}`;
  });

  function setSelectedRuntimeTarget(runtimeTarget: string): void {
    const workspaceId = input.currentWorkspace.value?.workspace_id;
    if (!workspaceId) {
      return;
    }
    writeComposerRuntimePrefs(workspaceId, { runtime_target: runtimeTarget });
    input.composerRuntimePrefsRevision.value += 1;
  }

  function setSelectedComposerModel(modelId: string): void {
    const workspaceId = input.currentWorkspace.value?.workspace_id;
    if (!workspaceId) {
      return;
    }
    const target = selectedRuntimeTargetId.value;
    const targetRecord = [
      ...(input.runtimeStatus.value?.local ?? []),
      ...(input.runtimeStatus.value?.cloud ?? []),
    ].find((record) => record.id === target);
    const family = targetRecord?.family ?? 'cursor';
    const normalized = modelId.trim() || 'auto';
    if (family === 'codex') {
      writeComposerRuntimePrefs(workspaceId, { codex_cli_model: normalized });
    } else if (family === 'claude') {
      writeComposerRuntimePrefs(workspaceId, { claude_cli_model: normalized });
    } else {
      writeComposerRuntimePrefs(workspaceId, { cursor_cli_model: normalized });
      // Server-side pin so continuous workers honor Auto/Composer vs explicit API.
      void saveWorkspaceComposerPrefs(workspaceId, { cursor_cli_model: normalized }).catch(
        () => undefined,
      );
    }
    input.composerRuntimePrefsRevision.value += 1;
  }

  function toggleCursorPickerVisibleModel(modelId: string): void {
    toggleCursorPickerVisibleModelPref(modelId, readCursorPickerVisibleModelIds());
    input.cursorPickerVisibleRevision.value += 1;
  }

  return {
    composerRuntimePrefs,
    selectedRuntimeTargetId,
    selectedComposerModel,
    cursorCatalogRows,
    codexCatalogRows,
    cursorPickerVisibleModelIds,
    composerRuntimeLabel,
    setSelectedRuntimeTarget,
    setSelectedComposerModel,
    toggleCursorPickerVisibleModel,
  };
}

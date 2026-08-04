import { computed, type ComputedRef, type Ref } from 'vue';

import type {
  ClaudeRuntimeStatusSnapshot,
  CursorRuntimeStatusSnapshot,
  RuntimeStatusSnapshot,
} from '../../../api/control-plane';
import {
  buildClaudeCatalogRows,
  claudeRuntimeLabel,
  resolveClaudeModel,
  type ClaudeCatalogRow,
} from '../../../lib/claude-catalog-view';
import {
  buildCursorCatalogRows,
  composerRuntimeFamilyLabel,
  cursorComposerRuntimeLabel,
  resolveCursorComposerModel,
  type CursorCatalogRow,
} from '../../../lib/cursor-catalog-view';
import {
  readComposerRuntimePrefs,
  writeComposerRuntimePrefs,
} from '../../../lib/composer-runtime-prefs';
import {
  readClaudePickerVisibleModelIds,
  toggleClaudePickerVisibleModel as toggleClaudePickerVisibleModelPref,
} from '../../../lib/claude-picker-prefs';
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
  claudeRuntimeStatus: Ref<ClaudeRuntimeStatusSnapshot | null>;
  composerRuntimePrefsRevision: Ref<number>;
  cursorPickerVisibleRevision: Ref<number>;
  claudePickerVisibleRevision: Ref<number>;
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

  const claudeCatalogRows: ComputedRef<ClaudeCatalogRow[]> = computed(() =>
    buildClaudeCatalogRows(input.claudeRuntimeStatus.value),
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
      const stored = prefs.claude_cli_model?.trim();
      if (!stored || stored === 'auto') {
        return stored || 'auto';
      }
      return resolveClaudeModel(stored, claudeCatalogRows.value);
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

  const claudePickerVisibleModelIds = computed(() => {
    input.claudePickerVisibleRevision.value;
    return readClaudePickerVisibleModelIds();
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
    if (family === 'claude') {
      return claudeRuntimeLabel({
        family,
        modelId: selectedComposerModel.value,
        rows: claudeCatalogRows.value,
      });
    }
    const model = selectedComposerModel.value;
    const modelLabel = model === 'auto' ? 'Auto' : model;
    return `${composerRuntimeFamilyLabel(family)} · ${modelLabel}`;
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

  function toggleClaudePickerVisibleModel(modelId: string): void {
    toggleClaudePickerVisibleModelPref(modelId, readClaudePickerVisibleModelIds());
    input.claudePickerVisibleRevision.value += 1;
  }

  return {
    composerRuntimePrefs,
    selectedRuntimeTargetId,
    selectedComposerModel,
    cursorCatalogRows,
    claudeCatalogRows,
    cursorPickerVisibleModelIds,
    claudePickerVisibleModelIds,
    composerRuntimeLabel,
    setSelectedRuntimeTarget,
    setSelectedComposerModel,
    toggleCursorPickerVisibleModel,
    toggleClaudePickerVisibleModel,
  };
}

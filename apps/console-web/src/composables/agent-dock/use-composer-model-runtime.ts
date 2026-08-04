import { computed, type Ref } from 'vue';

import {
  runtimeNeedsVaultAction,
  runtimeVaultHint,
} from '../../lib/agent-dock-runtime-view';
import { navigateToAppSurface } from '../../lib/app-surface-route';
import {
  claudeAutoModelDescription,
  claudeCatalogCountLabel,
  claudeCatalogModelRows,
  claudeCatalogStatusLabel,
  claudeManageModelRows,
  claudeModelLabel,
  claudePrimaryModelRows,
  claudePrimaryPickerRowsForActiveModel,
  claudeStaleModelWarning,
  isClaudeAutoModel,
  isClaudePrimaryModel,
  shouldShowClaudeManualModelCatalog,
} from '../../lib/claude-catalog-view';
import { CLAUDE_PICKER_DEFAULT_MODEL } from '../../lib/claude-picker-prefs';
import {
  cursorAutoModelDescription,
  cursorCatalogCountLabel,
  cursorCatalogModelRows,
  cursorCatalogStatusLabel,
  cursorComposerPickerRowsForActiveModel,
  cursorManageModelRows,
  cursorModelLabel,
  cursorPrimaryModelRows,
  cursorStaleModelWarning,
  composerRuntimeFamilyLabel,
  isCursorAutoModel,
  isCursorComposerModel,
  type CursorCatalogRow,
  shouldShowCursorManualModelCatalog,
} from '../../lib/cursor-catalog-view';
import { CURSOR_PICKER_COMPOSER_IDS, CURSOR_PICKER_DEFAULT_MODEL } from '../../lib/cursor-picker-prefs';
import { composerClaudeAuthLine, composerCursorAuthLine } from '../../lib/runtime-auth-view';
import { useShellStore } from '../../stores/shell';

type ShellStore = ReturnType<typeof useShellStore>;

type UseComposerModelRuntimeOptions = {
  showAddModelsPanel: Ref<boolean>;
  showRuntimeTargetsPanel: Ref<boolean>;
  modelSearchQuery: Ref<string>;
  closeMenus: () => void;
};

/** Only these families have a model catalog picker today — everything else falls back to a plain label. */
type CatalogFamily = 'cursor' | 'claude';

export function useComposerModelRuntime(
  shell: ShellStore,
  options: UseComposerModelRuntimeOptions,
) {
  const { showAddModelsPanel, showRuntimeTargetsPanel, modelSearchQuery, closeMenus } = options;

  const runtimeTargets = computed(() => {
    const status = shell.runtimeStatus;
    if (!status) return [];
    return [...status.local, ...status.cloud];
  });
  const currentRuntimeTarget = computed(() => {
    const preferred = shell.selectedRuntimeTargetId;
    const status = shell.runtimeStatus;
    if (!status) return null;
    const records = [...status.local, ...status.cloud];
    if (preferred) {
      return records.find((record) => record.id === preferred) ?? records[0] ?? null;
    }
    const defaultRuntime = status.default_runtime;
    if (!defaultRuntime) return records[0] ?? null;
    return records.find((record) => record.id === defaultRuntime) ?? null;
  });
  /** Cursor stays the default catalog when no target is selected yet — matches prior behavior. */
  const catalogFamily = computed<CatalogFamily | null>(() => {
    const family = currentRuntimeTarget.value?.family ?? 'cursor';
    if (family === 'cursor') return 'cursor';
    if (family === 'claude') return 'claude';
    return null;
  });
  const showModelCatalog = computed(() => catalogFamily.value !== null);
  const isClaudeCatalog = computed(() => catalogFamily.value === 'claude');

  const selectedModelId = computed(() => shell.selectedComposerModel || 'auto');
  const selectedModelLabel = computed(() =>
    isClaudeCatalog.value
      ? claudeModelLabel(selectedModelId.value, shell.claudeCatalogRows)
      : cursorModelLabel(selectedModelId.value, shell.cursorCatalogRows),
  );
  const runtimeFamilyLabel = computed(() => {
    const target = currentRuntimeTarget.value;
    if (target?.family) {
      return composerRuntimeFamilyLabel(target.family);
    }
    return 'Runtime';
  });
  /** Model chip text — model only (Auto / Composer / …). */
  const runtimeLabel = computed(() => selectedModelLabel.value);
  const runtimeDetail = computed(() => {
    if (shell.composerRuntimeLabel) {
      return shell.composerRuntimeLabel;
    }
    return `${runtimeFamilyLabel.value} · ${selectedModelLabel.value}`;
  });
  const autoModelRow = computed(() => {
    if (isClaudeCatalog.value) {
      return (
        shell.claudeCatalogRows.find((row) => row.id === 'auto') ?? {
          id: 'auto',
          label: 'Auto',
          description: claudeAutoModelDescription(shell.claudeCatalogRows),
          available: true,
        }
      );
    }
    return (
      shell.cursorCatalogRows.find((row) => row.id === 'auto') ?? {
        id: 'auto',
        label: 'Auto',
        description: cursorAutoModelDescription(shell.cursorCatalogRows),
        available: true,
      }
    );
  });
  const composerPickerRows = computed(() => {
    if (isClaudeCatalog.value) {
      return claudePrimaryPickerRowsForActiveModel({
        rows: shell.claudeCatalogRows,
        activeModelId: selectedModelId.value,
      });
    }
    const fromCatalog = cursorComposerPickerRowsForActiveModel({
      rows: shell.cursorCatalogRows,
      activeModelId: selectedModelId.value,
    });
    if (fromCatalog.length) {
      return fromCatalog;
    }
    if (!shouldShowCursorManualModelCatalog(selectedModelId.value)) {
      return [];
    }
    return CURSOR_PICKER_COMPOSER_IDS.map((id): CursorCatalogRow => ({
      id,
      label: id,
      description:
        id === CURSOR_PICKER_DEFAULT_MODEL
          ? 'Cursor Composer default — use when API quota models fail'
          : 'Cursor Composer model',
      available: true,
    }));
  });
  const extraPinnedRows = computed(() => {
    if (isClaudeCatalog.value) {
      return claudePrimaryModelRows({
        rows: shell.claudeCatalogRows,
        activeModelId: selectedModelId.value,
        visibleExtraModelIds: shell.claudePickerVisibleModelIds,
      }).filter((row) => !isClaudePrimaryModel(row.id));
    }
    return cursorPrimaryModelRows({
      rows: shell.cursorCatalogRows,
      activeModelId: selectedModelId.value,
      visibleExtraModelIds: shell.cursorPickerVisibleModelIds,
    }).filter((row) => !isCursorComposerModel(row.id));
  });
  const cursorManageRows = computed(() => {
    if (isClaudeCatalog.value) {
      return claudeManageModelRows({
        rows: shell.claudeCatalogRows,
        searchQuery: modelSearchQuery.value,
      });
    }
    return cursorManageModelRows({
      rows: shell.cursorCatalogRows,
      searchQuery: modelSearchQuery.value,
    });
  });
  const cursorCatalogStatus = computed(() => {
    if (isClaudeCatalog.value) {
      return claudeCatalogStatusLabel({
        loading: shell.claudeCatalogLoadState === 'loading',
        snapshot: shell.claudeRuntimeStatus,
      });
    }
    return cursorCatalogStatusLabel({
      loading: shell.cursorCatalogLoadState === 'loading',
      snapshot: shell.cursorRuntimeStatus,
    });
  });
  const cursorCatalogCount = computed(() => {
    if (isClaudeCatalog.value) {
      return claudeCatalogCountLabel({
        rows: shell.claudeCatalogRows,
        visibleExtraModelIds: shell.claudePickerVisibleModelIds,
        searchQuery: modelSearchQuery.value,
      });
    }
    return cursorCatalogCountLabel({
      rows: shell.cursorCatalogRows,
      visibleExtraModelIds: shell.cursorPickerVisibleModelIds,
      searchQuery: modelSearchQuery.value,
    });
  });
  const cursorStaleWarning = computed(() => {
    if (isClaudeCatalog.value) {
      return claudeStaleModelWarning({
        modelId: selectedModelId.value,
        rows: shell.claudeCatalogRows,
        snapshot: shell.claudeRuntimeStatus,
      });
    }
    return cursorStaleModelWarning({
      modelId: selectedModelId.value,
      rows: shell.cursorCatalogRows,
      snapshot: shell.cursorRuntimeStatus,
    });
  });
  const cursorAuthLine = computed(() => {
    if (isClaudeCatalog.value) {
      return composerClaudeAuthLine({
        target: currentRuntimeTarget.value,
        claudeSnapshot: shell.claudeRuntimeStatus,
      });
    }
    return composerCursorAuthLine({
      target: currentRuntimeTarget.value,
      cursorSnapshot: shell.cursorRuntimeStatus,
    });
  });
  const selectedRuntimeSummary = computed(() => {
    const target = currentRuntimeTarget.value;
    if (!target) {
      return 'No runtime selected';
    }
    const status = target.ready ? 'Ready' : runtimeStatusLine(target);
    return `${composerRuntimeFamilyLabel(target.family)} · ${status}`;
  });
  const autoModelEnabled = computed(() =>
    isClaudeCatalog.value
      ? isClaudeAutoModel(selectedModelId.value)
      : isCursorAutoModel(selectedModelId.value),
  );
  const showAddModelsEntry = computed(() => {
    if (showAddModelsPanel.value) return false;
    return isClaudeCatalog.value
      ? shouldShowClaudeManualModelCatalog(selectedModelId.value)
      : shouldShowCursorManualModelCatalog(selectedModelId.value);
  });
  const autoToggleChecked = computed(() => autoModelEnabled.value && !showAddModelsPanel.value);
  const showExtraPinnedRows = computed(
    () => extraPinnedRows.value.length > 0 && !showAddModelsPanel.value,
  );
  const cursorCatalogTotal = computed(() =>
    isClaudeCatalog.value
      ? claudeCatalogModelRows(shell.claudeCatalogRows).length
      : cursorCatalogModelRows(shell.cursorCatalogRows).length,
  );
  /** "Loading Cursor models…" / "Loading Claude models…" — active-family loading note. */
  const modelCatalogLoadingLabel = computed(
    () => `Loading ${runtimeFamilyLabel.value} models…`,
  );
  const modelCatalogLoading = computed(() =>
    isClaudeCatalog.value
      ? shell.claudeCatalogLoadState === 'loading'
      : shell.cursorCatalogLoadState === 'loading',
  );
  const modelCatalogErrorMessage = computed(() =>
    isClaudeCatalog.value ? shell.claudeCatalogError ?? '' : shell.cursorCatalogError ?? '',
  );
  /** Cursor alone has a live-vs-fallback split — Claude's catalog is always static. */
  const showFallbackCatalogNote = computed(
    () => !isClaudeCatalog.value && shell.cursorRuntimeStatus?.catalog_source === 'fallback',
  );
  const runtimeHint = computed(() => {
    if (shell.runtimeStatusError) {
      return shell.runtimeStatusError;
    }
    if (runtimeNeedsVaultAction(shell.runtimeStatus)) {
      return runtimeVaultHint(shell.runtimeStatus);
    }
    const target = currentRuntimeTarget.value;
    if (target?.ready) {
      return target.auth.message || 'Runtime is ready.';
    }
    if (target?.auth?.message) {
      return target.auth.message;
    }
    return 'Axon-X owns routing and falls back between configured runtimes.';
  });
  const showVaultAction = computed(() => runtimeNeedsVaultAction(shell.runtimeStatus));

  function openAddModelsPanel(): void {
    showAddModelsPanel.value = true;
  }

  function closeAddModelsPanel(): void {
    showAddModelsPanel.value = false;
    modelSearchQuery.value = '';
  }

  function selectRuntimeTarget(runtimeId: string): void {
    shell.setSelectedRuntimeTarget(runtimeId);
  }

  function selectComposerModel(modelId: string, options?: { keepMenuOpen?: boolean }): void {
    shell.setSelectedComposerModel(modelId);
    if (!options?.keepMenuOpen) {
      closeMenus();
    }
  }

  function toggleRuntimeTargetsPanel(): void {
    showRuntimeTargetsPanel.value = !showRuntimeTargetsPanel.value;
  }

  function onAutoToggleClick(event: MouseEvent): void {
    event.preventDefault();
    event.stopPropagation();
    const fallbackDefault = isClaudeCatalog.value
      ? CLAUDE_PICKER_DEFAULT_MODEL
      : CURSOR_PICKER_DEFAULT_MODEL;
    if (autoModelEnabled.value && !showAddModelsPanel.value) {
      selectComposerModel(fallbackDefault, { keepMenuOpen: true });
      return;
    }
    selectComposerModel('auto', { keepMenuOpen: true });
    closeAddModelsPanel();
  }

  function selectManageModelRow(modelId: string): void {
    selectComposerModel(modelId);
  }

  function openVaultSurface(): void {
    navigateToAppSurface('vault');
  }

  function runtimeStatusLine(record: (typeof runtimeTargets.value)[number]): string {
    if (record.ready) return 'Ready';
    if (!record.available) return 'Not installed';
    return record.auth.message || 'Installed but not ready';
  }

  return {
    autoModelRow,
    autoToggleChecked,
    closeAddModelsPanel,
    composerPickerRows,
    cursorAuthLine,
    cursorCatalogCount,
    cursorCatalogStatus,
    cursorCatalogTotal,
    cursorManageRows,
    cursorStaleWarning,
    currentRuntimeTarget,
    extraPinnedRows,
    modelCatalogErrorMessage,
    modelCatalogLoading,
    modelCatalogLoadingLabel,
    onAutoToggleClick,
    openAddModelsPanel,
    openVaultSurface,
    runtimeDetail,
    runtimeFamilyLabel,
    runtimeHint,
    runtimeLabel,
    runtimeStatusLine,
    runtimeTargets,
    selectComposerModel,
    selectManageModelRow,
    selectRuntimeTarget,
    selectedModelId,
    selectedModelLabel,
    selectedRuntimeSummary,
    showAddModelsEntry,
    showModelCatalog,
    showExtraPinnedRows,
    showFallbackCatalogNote,
    showVaultAction,
    toggleRuntimeTargetsPanel,
  };
}

import { computed, toValue, type MaybeRef } from 'vue';

import { MODE_OPTIONS, type ComposerMode } from './use-composer-menus';
import type { AgentDockComposerAttachmentChip } from '../../components/ide/agent-dock/agent-dock-composer-toolbar-types';
import type { ComposerMcpTool } from '../../lib/composer-mcp-tools-view';
import type { ClaudeCatalogRow } from '../../lib/claude-catalog-view';
import type { CursorCatalogRow } from '../../lib/cursor-catalog-view';
import type { AgentDockComposerRuntimeTarget } from '../../components/ide/agent-dock/agent-dock-composer-toolbar-types';

type ModeOption = (typeof MODE_OPTIONS)[number];

/** Fields the composer API must expose for the toolbar binding. */
export type AgentDockComposerToolbarSource = {
  showContextMenu: MaybeRef<boolean>;
  showToolsMenu: MaybeRef<boolean>;
  showModelMenu: MaybeRef<boolean>;
  showModeMenu: MaybeRef<boolean>;
  showAddModelsPanel: MaybeRef<boolean>;
  showRuntimeTargetsPanel: MaybeRef<boolean>;
  showAddModelsEntry: MaybeRef<boolean>;
  showExtraPinnedRows: MaybeRef<boolean>;
  showModelCatalog: MaybeRef<boolean>;
  isClaudeCatalog: MaybeRef<boolean>;
  claudeFlatRows: MaybeRef<ClaudeCatalogRow[]>;
  showFallbackCatalogNote: MaybeRef<boolean>;
  showCursorCatalog: MaybeRef<boolean>;
  showCodexCatalog: MaybeRef<boolean>;
  showVaultAction: MaybeRef<boolean>;
  attachmentChips: MaybeRef<AgentDockComposerAttachmentChip[]>;
  composerImages: MaybeRef<unknown[]>;
  mcpToolsForMode: MaybeRef<ComposerMcpTool[]>;
  composerMode: MaybeRef<ComposerMode>;
  MODE_OPTIONS: ModeOption[];
  modeButtonLabel: MaybeRef<string>;
  modeButtonTitle: MaybeRef<string>;
  activeMode: MaybeRef<ModeOption>;
  isFullAccessAgent: MaybeRef<boolean>;
  executionAccessHint: MaybeRef<string>;
  sandboxSessionEnabled: MaybeRef<boolean>;
  sandboxEnvForced: MaybeRef<boolean>;
  sandboxHint: MaybeRef<string>;
  sandboxLabel: MaybeRef<string>;
  sandboxSessionPending: MaybeRef<boolean>;
  contextWorkspace: MaybeRef<boolean>;
  contextSelection: MaybeRef<boolean>;
  contextTerminal: MaybeRef<boolean>;
  contextIde: MaybeRef<boolean>;
  contextPinned: MaybeRef<boolean>;
  hasTerminalSnippet: MaybeRef<boolean>;
  selectionChipLabel: MaybeRef<string>;
  runtimeDetail: MaybeRef<string>;
  runtimeFamilyLabel: MaybeRef<string>;
  runtimeLabel: MaybeRef<string>;
  selectedRuntimeSummary: MaybeRef<string>;
  runtimeTargets: MaybeRef<AgentDockComposerRuntimeTarget[]>;
  selectedModelId: MaybeRef<string>;
  selectedModelLabel: MaybeRef<string>;
  autoModelRow: MaybeRef<CursorCatalogRow>;
  autoToggleChecked: MaybeRef<boolean>;
  composerPickerRows: MaybeRef<CursorCatalogRow[]>;
  extraPinnedRows: MaybeRef<CursorCatalogRow[]>;
  cursorCatalogTotal: MaybeRef<number>;
  cursorCatalogStatus: MaybeRef<string>;
  cursorAuthLine: MaybeRef<string>;
  cursorStaleWarning: MaybeRef<string | null>;
  cursorManageRows: MaybeRef<CursorCatalogRow[]>;
  cursorCatalogCount: MaybeRef<string>;
  modelCatalogLoading: MaybeRef<boolean>;
  modelCatalogLoadingLabel: MaybeRef<string>;
  modelCatalogErrorMessage: MaybeRef<string>;
  codexCatalogRows: MaybeRef<CursorCatalogRow[]>;
  codexCatalogStatus: MaybeRef<string>;
  modelSearchQuery: MaybeRef<string>;
  runtimeHint: MaybeRef<string>;
  canConvertInstructions: MaybeRef<boolean>;
  instructionsGenerating: MaybeRef<boolean>;
};

/** Bind composer setup refs into toolbar prop values (keeps AgentDockComposer.vue thin). */
export function useAgentDockComposerToolbarProps(
  composer: AgentDockComposerToolbarSource,
) {
  return computed(() => ({
    showContextMenu: toValue(composer.showContextMenu),
    showToolsMenu: toValue(composer.showToolsMenu),
    showModelMenu: toValue(composer.showModelMenu),
    showModeMenu: toValue(composer.showModeMenu),
    showAddModelsPanel: toValue(composer.showAddModelsPanel),
    showRuntimeTargetsPanel: toValue(composer.showRuntimeTargetsPanel),
    showAddModelsEntry: toValue(composer.showAddModelsEntry),
    showExtraPinnedRows: toValue(composer.showExtraPinnedRows),
    showModelCatalog: toValue(composer.showModelCatalog),
    isClaudeCatalog: toValue(composer.isClaudeCatalog),
    claudeFlatRows: toValue(composer.claudeFlatRows),
    showFallbackCatalogNote: toValue(composer.showFallbackCatalogNote),
    showCursorCatalog: toValue(composer.showCursorCatalog),
    showCodexCatalog: toValue(composer.showCodexCatalog),
    showVaultAction: toValue(composer.showVaultAction),
    attachmentChips: toValue(composer.attachmentChips),
    composerImageCount: toValue(composer.composerImages).length,
    mcpToolsForMode: toValue(composer.mcpToolsForMode),
    composerMode: toValue(composer.composerMode),
    modeOptions: composer.MODE_OPTIONS,
    modeButtonLabel: toValue(composer.modeButtonLabel),
    modeButtonTitle: toValue(composer.modeButtonTitle),
    activeMode: toValue(composer.activeMode),
    isFullAccessAgent: toValue(composer.isFullAccessAgent),
    executionAccessHint: toValue(composer.executionAccessHint),
    sandboxSessionEnabled: toValue(composer.sandboxSessionEnabled),
    sandboxEnvForced: toValue(composer.sandboxEnvForced),
    sandboxHint: toValue(composer.sandboxHint),
    sandboxLabel: toValue(composer.sandboxLabel),
    sandboxSessionPending: toValue(composer.sandboxSessionPending),
    contextWorkspace: toValue(composer.contextWorkspace),
    contextSelection: toValue(composer.contextSelection),
    contextTerminal: toValue(composer.contextTerminal),
    contextIde: toValue(composer.contextIde),
    contextPinned: toValue(composer.contextPinned),
    hasTerminalSnippet: toValue(composer.hasTerminalSnippet),
    selectionChipLabel: toValue(composer.selectionChipLabel),
    runtimeDetail: toValue(composer.runtimeDetail),
    runtimeFamilyLabel: toValue(composer.runtimeFamilyLabel),
    runtimeLabel: toValue(composer.runtimeLabel),
    selectedRuntimeSummary: toValue(composer.selectedRuntimeSummary),
    runtimeTargets: toValue(composer.runtimeTargets),
    selectedModelId: toValue(composer.selectedModelId),
    selectedModelLabel: toValue(composer.selectedModelLabel),
    autoModelRow: toValue(composer.autoModelRow),
    autoToggleChecked: toValue(composer.autoToggleChecked),
    composerPickerRows: toValue(composer.composerPickerRows),
    extraPinnedRows: toValue(composer.extraPinnedRows),
    cursorCatalogTotal: toValue(composer.cursorCatalogTotal),
    cursorCatalogStatus: toValue(composer.cursorCatalogStatus),
    cursorAuthLine: toValue(composer.cursorAuthLine),
    cursorStaleWarning: toValue(composer.cursorStaleWarning) ?? '',
    cursorManageRows: toValue(composer.cursorManageRows),
    cursorCatalogCount: toValue(composer.cursorCatalogCount),
    modelCatalogLoading: toValue(composer.modelCatalogLoading),
    modelCatalogLoadingLabel: toValue(composer.modelCatalogLoadingLabel),
    modelCatalogErrorMessage: toValue(composer.modelCatalogErrorMessage),
    codexCatalogRows: toValue(composer.codexCatalogRows),
    codexCatalogStatus: toValue(composer.codexCatalogStatus),
    modelSearchQuery: toValue(composer.modelSearchQuery),
    runtimeHint: toValue(composer.runtimeHint),
    canConvertInstructions: toValue(composer.canConvertInstructions),
    instructionsGenerating: toValue(composer.instructionsGenerating),
  }));
}

export const PLAN_SOFT_SWITCH_REASON_LABEL: Record<string, string> = {
  planning_phrase: 'planning phrasing',
  bullet_heavy: 'structured list',
  long_multistep: 'long multi-step ask',
  plan_keyword: 'plan keyword',
  explicit_plan_request: 'explicit plan request',
};

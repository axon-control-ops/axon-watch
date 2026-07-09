import { computed, type Ref, ref } from 'vue';

import {
  agentExecutionAccessHint,
  agentExecutionAccessLabel,
} from '../../lib/agent-execution-access-prefs';
import { OPERATOR_PERSONA_NAME } from '../../lib/operator-persona-name';
import { useShellStore } from '../../stores/shell';

export type ComposerMode = 'agent' | 'plan' | 'ask' | 'kairo';

export const MODE_OPTIONS: Array<{
  key: ComposerMode;
  label: string;
  icon: string;
  hint: string;
}> = [
  { key: 'ask', label: 'Ask', icon: '◯', hint: 'Read-only answers, no tool execution' },
  { key: 'plan', label: 'Plan', icon: '◈', hint: 'Map steps before executing' },
  { key: 'agent', label: 'Agent', icon: '◎', hint: 'Agent loop with tools and approvals' },
  { key: 'kairo', label: OPERATOR_PERSONA_NAME, icon: '◉', hint: `Talk to ${OPERATOR_PERSONA_NAME} — spoken replies` },
];

type ShellStore = ReturnType<typeof useShellStore>;

type UseComposerMenusOptions = {
  composerMode: Ref<ComposerMode>;
};

export function useComposerMenus(shell: ShellStore, options: UseComposerMenusOptions) {
  const { composerMode } = options;

  const showContextMenu = ref(false);
  const showToolsMenu = ref(false);
  const showModelMenu = ref(false);
  const showModeMenu = ref(false);
  const showFullAccessConsent = ref(false);
  const fullAccessConsentChecked = ref(false);
  const showAddModelsPanel = ref(false);
  const showRuntimeTargetsPanel = ref(false);
  const modelSearchQuery = ref('');

  const activeMode = computed(
    () => MODE_OPTIONS.find((option) => option.key === composerMode.value) ?? MODE_OPTIONS[2],
  );
  const showApprovalBanner = computed(
    () =>
      composerMode.value === 'agent' &&
      shell.agentExecutionAccess === 'full' &&
      shell.ideAgentLinkedRun?.phase === 'awaiting_approval',
  );
  const executionAccessLabel = computed(() =>
    agentExecutionAccessLabel(shell.agentExecutionAccess),
  );
  const executionAccessHint = computed(() =>
    agentExecutionAccessHint(shell.agentExecutionAccess),
  );
  const isFullAccessAgent = computed(
    () => composerMode.value === 'agent' && shell.agentExecutionAccess === 'full',
  );
  const modeButtonLabel = computed(() => {
    if (isFullAccessAgent.value) {
      return 'Agent · Full';
    }
    return activeMode.value.label;
  });

  function closeMenus(): void {
    showContextMenu.value = false;
    showToolsMenu.value = false;
    showModelMenu.value = false;
    showModeMenu.value = false;
    showAddModelsPanel.value = false;
    showRuntimeTargetsPanel.value = false;
    modelSearchQuery.value = '';
  }

  function toggleSection(section: 'context' | 'tools' | 'model' | 'mode'): void {
    showContextMenu.value = section === 'context' ? !showContextMenu.value : false;
    const openingTools = section === 'tools' ? !showToolsMenu.value : false;
    showToolsMenu.value = openingTools;
    const openingModel = section === 'model' ? !showModelMenu.value : false;
    showModelMenu.value = openingModel;
    showModeMenu.value = section === 'mode' ? !showModeMenu.value : false;
    if (!openingModel) {
      showAddModelsPanel.value = false;
      showRuntimeTargetsPanel.value = false;
      modelSearchQuery.value = '';
    }
    if (openingTools) {
      void shell.loadRuntimeMcpTools();
    }
    if (openingModel) {
      void Promise.all([shell.loadRuntimeStatus(), shell.loadCursorCatalog(true)]);
    }
  }

  function selectMode(mode: ComposerMode): void {
    composerMode.value = mode;
    showModeMenu.value = false;
  }

  function requestFullAccess(): void {
    if (shell.agentExecutionAccess === 'full') {
      return;
    }
    fullAccessConsentChecked.value = false;
    showFullAccessConsent.value = true;
    showModeMenu.value = false;
  }

  function cancelFullAccessConsent(): void {
    showFullAccessConsent.value = false;
    fullAccessConsentChecked.value = false;
  }

  function confirmFullAccessConsent(): void {
    if (!fullAccessConsentChecked.value) {
      return;
    }
    shell.setAgentExecutionAccess('full');
    showFullAccessConsent.value = false;
    fullAccessConsentChecked.value = false;
  }

  function switchToConsultativeAccess(): void {
    shell.setAgentExecutionAccess('consultative');
    showFullAccessConsent.value = false;
    fullAccessConsentChecked.value = false;
  }

  return {
    MODE_OPTIONS,
    activeMode,
    cancelFullAccessConsent,
    closeMenus,
    confirmFullAccessConsent,
    executionAccessHint,
    executionAccessLabel,
    fullAccessConsentChecked,
    isFullAccessAgent,
    modeButtonLabel,
    modelSearchQuery,
    requestFullAccess,
    selectMode,
    showAddModelsPanel,
    showApprovalBanner,
    showContextMenu,
    showFullAccessConsent,
    showModeMenu,
    showModelMenu,
    showRuntimeTargetsPanel,
    showToolsMenu,
    switchToConsultativeAccess,
    toggleSection,
  };
}

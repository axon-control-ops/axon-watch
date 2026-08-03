import { computed, type Ref, ref } from 'vue';

import {
  disableSandboxSession,
  enableSandboxSession,
  fetchSandboxSessionStatus,
} from '../../api/safe-improvement-api';
import {
  agentExecutionAccessHint,
  agentExecutionAccessLabel,
} from '../../lib/agent-execution-access-prefs';
import { isToolCapableComposerMode } from '../../lib/composer-tool-modes';
import { OPERATOR_PERSONA_NAME } from '../../lib/operator-persona-name';
import {
  buildComposerModeAccessLabel,
  sandboxSessionHint,
  sandboxSessionLabel,
} from '../../lib/sandbox-session-view';
import { useShellStore } from '../../stores/shell';

export type ComposerMode = 'agent' | 'plan' | 'ask' | 'debug' | 'kairo';

export const MODE_OPTIONS: Array<{
  key: ComposerMode;
  label: string;
  icon: string;
  hint: string;
}> = [
  {
    key: 'ask',
    label: 'Ask',
    icon: '◯',
    hint: 'Simple conversation — answers only, no edits or tools',
  },
  { key: 'plan', label: 'Plan', icon: '◈', hint: 'Map steps before executing a task' },
  {
    key: 'debug',
    label: 'Debug',
    icon: '⌖',
    hint: 'Hypothesize, instrument, reproduce, then fix with evidence',
  },
  {
    key: 'agent',
    label: 'Agent',
    icon: '◎',
    hint: 'Do the task — tools, edits, and approvals',
  },
  {
    key: 'kairo',
    label: OPERATOR_PERSONA_NAME,
    icon: '◉',
    hint: `Talk to ${OPERATOR_PERSONA_NAME} — spoken replies`,
  },
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
  const showSandboxConsent = ref(false);
  const sandboxConsentChecked = ref(false);
  const sandboxSessionEnabled = ref(false);
  const sandboxEnvForced = ref(false);
  const sandboxSessionPending = ref(false);
  const sandboxSessionError = ref('');
  const showAddModelsPanel = ref(false);
  const showRuntimeTargetsPanel = ref(false);
  const modelSearchQuery = ref('');

  const activeMode = computed(
    () => MODE_OPTIONS.find((option) => option.key === composerMode.value) ?? MODE_OPTIONS[3],
  );
  const showApprovalBanner = computed(
    () =>
      isToolCapableComposerMode(composerMode.value) &&
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
    () =>
      isToolCapableComposerMode(composerMode.value) && shell.agentExecutionAccess === 'full',
  );
  const sandboxHint = computed(() =>
    sandboxSessionHint(sandboxSessionEnabled.value, sandboxEnvForced.value),
  );
  const sandboxLabel = computed(() => sandboxSessionLabel(sandboxSessionEnabled.value));
  const modeButtonLabel = computed(() =>
    buildComposerModeAccessLabel({
      modeLabel: activeMode.value.label,
      fullAccess: isFullAccessAgent.value,
      sandboxEnabled: sandboxSessionEnabled.value,
    }),
  );
  const modeButtonTitle = computed(() => {
    if (sandboxSessionEnabled.value && isFullAccessAgent.value) {
      return `${executionAccessHint.value} · ${sandboxHint.value}`;
    }
    if (sandboxSessionEnabled.value) {
      return sandboxHint.value;
    }
    if (isFullAccessAgent.value) {
      return executionAccessHint.value;
    }
    return activeMode.value.hint;
  });

  async function refreshSandboxSession(): Promise<void> {
    try {
      const status = await fetchSandboxSessionStatus();
      sandboxSessionEnabled.value = status.enabled;
      sandboxEnvForced.value = status.env_forced;
      sandboxSessionError.value = '';
    } catch (error) {
      sandboxSessionError.value =
        error instanceof Error ? error.message : 'Could not load Sandbox status.';
    }
  }

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
    const openingMode = section === 'mode' ? !showModeMenu.value : false;
    showModeMenu.value = openingMode;
    if (!openingModel) {
      showAddModelsPanel.value = false;
      showRuntimeTargetsPanel.value = false;
      modelSearchQuery.value = '';
    }
    if (openingTools) {
      void shell.loadRuntimeMcpTools();
    }
    if (openingModel) {
      void Promise.all([
        shell.loadRuntimeStatus(),
        shell.loadCursorCatalog(true),
        shell.loadCodexCatalog(true),
      ]);
    }
    if (openingMode) {
      void refreshSandboxSession();
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

  function requestSandboxSession(): void {
    if (sandboxSessionEnabled.value) {
      return;
    }
    sandboxConsentChecked.value = false;
    sandboxSessionError.value = '';
    showSandboxConsent.value = true;
    showModeMenu.value = false;
  }

  function cancelSandboxConsent(): void {
    if (sandboxSessionPending.value) {
      return;
    }
    showSandboxConsent.value = false;
    sandboxConsentChecked.value = false;
    sandboxSessionError.value = '';
  }

  async function confirmSandboxConsent(): Promise<void> {
    if (!sandboxConsentChecked.value || sandboxSessionPending.value) {
      return;
    }
    sandboxSessionPending.value = true;
    sandboxSessionError.value = '';
    try {
      const status = await enableSandboxSession();
      sandboxSessionEnabled.value = status.enabled;
      sandboxEnvForced.value = status.env_forced;
      showSandboxConsent.value = false;
      sandboxConsentChecked.value = false;
    } catch (error) {
      sandboxSessionError.value =
        error instanceof Error ? error.message : 'Could not enable Sandbox.';
    } finally {
      sandboxSessionPending.value = false;
    }
  }

  async function disableSandboxSessionAccess(): Promise<void> {
    if (sandboxEnvForced.value || sandboxSessionPending.value) {
      return;
    }
    sandboxSessionPending.value = true;
    sandboxSessionError.value = '';
    try {
      const status = await disableSandboxSession();
      sandboxSessionEnabled.value = status.enabled;
      sandboxEnvForced.value = status.env_forced;
      showModeMenu.value = false;
    } catch (error) {
      sandboxSessionError.value =
        error instanceof Error ? error.message : 'Could not turn Sandbox off.';
    } finally {
      sandboxSessionPending.value = false;
    }
  }

  return {
    MODE_OPTIONS,
    activeMode,
    cancelFullAccessConsent,
    cancelSandboxConsent,
    closeMenus,
    confirmFullAccessConsent,
    confirmSandboxConsent,
    disableSandboxSessionAccess,
    executionAccessHint,
    executionAccessLabel,
    fullAccessConsentChecked,
    isFullAccessAgent,
    modeButtonLabel,
    modeButtonTitle,
    modelSearchQuery,
    requestFullAccess,
    requestSandboxSession,
    sandboxConsentChecked,
    sandboxEnvForced,
    sandboxHint,
    sandboxLabel,
    sandboxSessionEnabled,
    sandboxSessionError,
    sandboxSessionPending,
    selectMode,
    showAddModelsPanel,
    showApprovalBanner,
    showContextMenu,
    showFullAccessConsent,
    showModeMenu,
    showModelMenu,
    showRuntimeTargetsPanel,
    showSandboxConsent,
    showToolsMenu,
    switchToConsultativeAccess,
    toggleSection,
  };
}

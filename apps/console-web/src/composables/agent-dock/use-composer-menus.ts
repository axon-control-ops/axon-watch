import { computed, type Ref, ref, watch } from 'vue';

import {
  disableComposerSandbox,
  discardComposerSandbox,
  enableComposerSandbox,
  fetchComposerSandboxStatus,
  publishComposerSandbox,
  reviewComposerSandbox,
} from '../../api/composer-sandbox-api';
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
  const sandboxAutoEnabled = ref(false);
  const sandboxManualEnabled = ref(false);
  const sandboxDirty = ref(false);
  const sandboxSource = ref('off');
  const sandboxSessionPending = ref(false);
  const sandboxSessionError = ref('');
  const sandboxChangedPaths = ref<string[]>([]);
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
  const effectiveExecutionAccess = computed(() =>
    sandboxSessionEnabled.value && isToolCapableComposerMode(composerMode.value)
      ? 'full'
      : shell.agentExecutionAccess,
  );
  const executionAccessLabel = computed(() => agentExecutionAccessLabel(effectiveExecutionAccess.value));
  const executionAccessHint = computed(() =>
    sandboxSessionEnabled.value && effectiveExecutionAccess.value === 'full'
      ? 'Full Access inside disposable isolation; external and protected effects remain gated'
      : agentExecutionAccessHint(effectiveExecutionAccess.value),
  );
  const isFullAccessAgent = computed(
    () =>
      isToolCapableComposerMode(composerMode.value) && effectiveExecutionAccess.value === 'full',
  );
  const sandboxHint = computed(() => {
    if (sandboxDirty.value && sandboxSource.value === 'retained') {
      return 'Full Auto ended; unpromoted changes are retained for review';
    }
    if (sandboxAutoEnabled.value) {
      return 'Full Auto provides lazy disposable isolation for this workspace';
    }
    return sandboxSessionHint(sandboxSessionEnabled.value, sandboxEnvForced.value);
  });
  const sandboxLabel = computed(() => {
    if (!sandboxSessionEnabled.value) return sandboxSessionLabel(false);
    if (sandboxSource.value === 'retained') return 'Sandbox · Retained changes';
    if (sandboxAutoEnabled.value && sandboxManualEnabled.value) return 'Sandbox · Auto + Manual';
    if (sandboxAutoEnabled.value) return 'Sandbox · Auto';
    return 'Sandbox · Manual';
  });
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
    const workspaceId = shell.currentWorkspace?.workspace_id;
    if (!workspaceId) {
      sandboxSessionEnabled.value = false;
      sandboxEnvForced.value = false;
      return;
    }
    try {
      const status = await fetchComposerSandboxStatus(workspaceId);
      if (shell.currentWorkspace?.workspace_id !== workspaceId) {
        return;
      }
      sandboxSessionEnabled.value = status.enabled;
      sandboxEnvForced.value = status.env_forced;
      sandboxAutoEnabled.value = status.auto_enabled;
      sandboxManualEnabled.value = status.manual_enabled;
      sandboxDirty.value = status.dirty;
      sandboxSource.value = status.source;
      sandboxSessionError.value = '';
    } catch (error) {
      sandboxSessionError.value =
        error instanceof Error ? error.message : 'Could not load Sandbox status.';
    }
  }

  // Sandbox sessions are explicitly per-workspace. Never carry the prior
  // workspace's badge/state into the next composer while its status loads.
  watch(
    () => `${shell.currentWorkspace?.workspace_id ?? ''}:${shell.operatorPresenceSettings.autonomy_mode}`,
    () => {
      sandboxSessionEnabled.value = false;
      sandboxEnvForced.value = false;
      sandboxAutoEnabled.value = false;
      sandboxManualEnabled.value = false;
      sandboxDirty.value = false;
      sandboxSource.value = 'off';
      sandboxSessionError.value = '';
      void refreshSandboxSession();
    },
    { immediate: true },
  );

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
        shell.loadClaudeCatalog(true),
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
    const workspaceId = shell.currentWorkspace?.workspace_id;
    if (!workspaceId) {
      sandboxSessionError.value = 'No workspace is open — cannot enable Sandbox.';
      return;
    }
    sandboxSessionPending.value = true;
    sandboxSessionError.value = '';
    try {
      const status = await enableComposerSandbox(workspaceId);
      sandboxSessionEnabled.value = status.enabled;
      sandboxEnvForced.value = status.env_forced;
      sandboxAutoEnabled.value = status.auto_enabled;
      sandboxManualEnabled.value = status.manual_enabled;
      sandboxDirty.value = status.dirty;
      sandboxSource.value = status.source;
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
    if (sandboxEnvForced.value || sandboxAutoEnabled.value || sandboxSessionPending.value) {
      return;
    }
    const workspaceId = shell.currentWorkspace?.workspace_id;
    if (!workspaceId) {
      return;
    }
    sandboxSessionPending.value = true;
    sandboxSessionError.value = '';
    try {
      const status = await disableComposerSandbox(workspaceId);
      sandboxSessionEnabled.value = status.enabled;
      sandboxEnvForced.value = status.env_forced;
      sandboxAutoEnabled.value = status.auto_enabled;
      sandboxManualEnabled.value = status.manual_enabled;
      sandboxDirty.value = status.dirty;
      sandboxSource.value = status.source;
      showModeMenu.value = false;
    } catch (error) {
      sandboxSessionError.value =
        error instanceof Error ? error.message : 'Could not turn Sandbox off.';
    } finally {
      sandboxSessionPending.value = false;
    }
  }

  async function reviewSandboxSessionChanges(): Promise<void> {
    const workspaceId = shell.currentWorkspace?.workspace_id;
    if (!workspaceId || sandboxSessionPending.value) return;
    sandboxSessionPending.value = true;
    try {
      const review = await reviewComposerSandbox(workspaceId);
      sandboxChangedPaths.value = review.changed_paths;
      sandboxDirty.value = review.dirty;
      sandboxSessionError.value = review.changed_paths.length
        ? `Retained changes: ${review.changed_paths.join(', ')}`
        : 'Sandbox has no unpromoted changes.';
    } catch (error) {
      sandboxSessionError.value = error instanceof Error ? error.message : 'Review failed.';
    } finally {
      sandboxSessionPending.value = false;
    }
  }

  async function publishSandboxSessionChanges(): Promise<void> {
    const workspaceId = shell.currentWorkspace?.workspace_id;
    if (!workspaceId || sandboxSessionPending.value) return;
    sandboxSessionPending.value = true;
    try {
      const status = await publishComposerSandbox(workspaceId);
      sandboxDirty.value = status.dirty;
      sandboxSessionEnabled.value = status.enabled;
      sandboxSessionError.value = 'Sandbox changes were published through workspace delivery.';
      await refreshSandboxSession();
    } catch (error) {
      sandboxSessionError.value = error instanceof Error ? error.message : 'Publish failed.';
    } finally {
      sandboxSessionPending.value = false;
    }
  }

  async function discardSandboxSessionChanges(): Promise<void> {
    const workspaceId = shell.currentWorkspace?.workspace_id;
    if (!workspaceId || sandboxSessionPending.value) return;
    if (!window.confirm('Permanently discard every unpromoted change in this Sandbox?')) return;
    sandboxSessionPending.value = true;
    try {
      await discardComposerSandbox(workspaceId);
      sandboxChangedPaths.value = [];
      sandboxSessionError.value = '';
      await refreshSandboxSession();
    } catch (error) {
      sandboxSessionError.value = error instanceof Error ? error.message : 'Discard failed.';
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
    discardSandboxSessionChanges,
    executionAccessHint,
    executionAccessLabel,
    fullAccessConsentChecked,
    isFullAccessAgent,
    modeButtonLabel,
    modeButtonTitle,
    modelSearchQuery,
    requestFullAccess,
    requestSandboxSession,
    publishSandboxSessionChanges,
    reviewSandboxSessionChanges,
    sandboxConsentChecked,
    sandboxChangedPaths,
    sandboxAutoEnabled,
    sandboxDirty,
    sandboxEnvForced,
    sandboxHint,
    sandboxLabel,
    sandboxManualEnabled,
    sandboxSource,
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

import type { Ref } from 'vue';

import {
  fetchOperatorPresenceSettings,
  saveOperatorPresenceSettings,
} from '../../../api/control-plane';
import type { OperatorPresenceSettings } from '../../../contracts/canonical';
import { navigateToAppSurface, readAppSurface } from '../../../lib/app-surface-route';
import {
  defaultOperatorPresenceSettings,
  normalizeOperatorPresenceSettings,
  persistOperatorPresenceSettings,
  readPersistedOperatorPresenceSettings,
} from '../../../lib/operator-presence-settings';
import type { AgentExecutionAccess } from '../../../lib/agent-execution-access-prefs';

interface CreateOperatorPresenceSettingsSliceInput {
  operatorPresenceSettings: Ref<OperatorPresenceSettings>;
  operatorPresenceSettingsOpen: Ref<boolean>;
  operatorPresenceSettingsSaving: Ref<boolean>;
  operatorPresenceSettingsError: Ref<string | null>;
  operatorPresenceSettingsSavedAt: Ref<number | null>;
  loadOperatorBriefing: () => Promise<void>;
  agentExecutionAccess: Ref<AgentExecutionAccess>;
  setAgentExecutionAccess: (value: AgentExecutionAccess) => void;
}

export function createOperatorPresenceSettingsSlice(
  input: CreateOperatorPresenceSettingsSliceInput,
) {
  let operatorPresenceSettingsSaveQueue: Promise<void> = Promise.resolve();

  function syncFullAutonomyExecutionAccess(settings: OperatorPresenceSettings): void {
    const shouldPromote = settings.autonomy_mode === 'full';
    const previousAccess = input.agentExecutionAccess.value;
    if (shouldPromote && previousAccess !== 'full') {
      input.setAgentExecutionAccess('full');
    }
  }

  async function loadOperatorPresenceSettings(options?: {
    reportError?: boolean;
  }): Promise<void> {
    const cached = readPersistedOperatorPresenceSettings();
    if (cached) {
      input.operatorPresenceSettings.value = cached;
    }

    try {
      const snapshot = await fetchOperatorPresenceSettings();
      input.operatorPresenceSettings.value = normalizeOperatorPresenceSettings(snapshot.settings);
      persistOperatorPresenceSettings(input.operatorPresenceSettings.value);
      syncFullAutonomyExecutionAccess(input.operatorPresenceSettings.value);
      input.operatorPresenceSettingsError.value = null;
    } catch (error) {
      if (options?.reportError) {
        input.operatorPresenceSettingsError.value =
          error instanceof Error ? error.message : 'operator presence settings load failed';
      }
    }
  }

  async function saveOperatorPresenceSettingsPatchImpl(
    patch: Partial<OperatorPresenceSettings>,
  ): Promise<void> {
    input.operatorPresenceSettingsSaving.value = true;
    input.operatorPresenceSettingsError.value = null;
    const previousSettings = input.operatorPresenceSettings.value;
    const nextSettings = normalizeOperatorPresenceSettings({
      ...input.operatorPresenceSettings.value,
      ...patch,
    });
    input.operatorPresenceSettings.value = nextSettings;
    persistOperatorPresenceSettings(nextSettings);

    try {
      const snapshot = await saveOperatorPresenceSettings(patch);
      input.operatorPresenceSettings.value = normalizeOperatorPresenceSettings(snapshot.settings);
      persistOperatorPresenceSettings(input.operatorPresenceSettings.value);
      syncFullAutonomyExecutionAccess(input.operatorPresenceSettings.value);
      input.operatorPresenceSettingsSavedAt.value = Date.now();
      input.operatorPresenceSettingsError.value = null;
      await input.loadOperatorBriefing();
    } catch (error) {
      input.operatorPresenceSettings.value = previousSettings;
      persistOperatorPresenceSettings(previousSettings);
      input.operatorPresenceSettingsError.value =
        error instanceof Error ? error.message : 'operator presence settings save failed';
      throw error instanceof Error
        ? error
        : new Error('operator presence settings save failed');
    } finally {
      input.operatorPresenceSettingsSaving.value = false;
    }
  }

  function saveOperatorPresenceSettingsPatch(
    patch: Partial<OperatorPresenceSettings>,
  ): Promise<void> {
    const run = (): Promise<void> => saveOperatorPresenceSettingsPatchImpl(patch);
    operatorPresenceSettingsSaveQueue = operatorPresenceSettingsSaveQueue.then(run, run);
    return operatorPresenceSettingsSaveQueue;
  }

  async function resetOperatorPresenceSettings(): Promise<void> {
    const defaults = defaultOperatorPresenceSettings();
    await saveOperatorPresenceSettingsPatch(defaults);
  }

  function openOperatorPresenceSettingsPanel(): void {
    input.operatorPresenceSettingsOpen.value = true;
    navigateToAppSurface('settings');
  }

  function toggleOperatorPresenceSettingsPanel(forceOpen?: boolean): void {
    if (forceOpen === false) {
      input.operatorPresenceSettingsOpen.value = false;
      if (readAppSurface() === 'settings') {
        navigateToAppSurface('console');
      }
      return;
    }
    openOperatorPresenceSettingsPanel();
  }

  return {
    loadOperatorPresenceSettings,
    saveOperatorPresenceSettingsPatch,
    resetOperatorPresenceSettings,
    openOperatorPresenceSettingsPanel,
    toggleOperatorPresenceSettingsPanel,
  };
}

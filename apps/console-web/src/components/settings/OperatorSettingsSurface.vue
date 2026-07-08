<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';

import AppGeneralSettingsPanel from './AppGeneralSettingsPanel.vue';
import OperatorPresenceSettingsForm from './OperatorPresenceSettingsForm.vue';
import RuntimeAuthSettingsPanel from './RuntimeAuthSettingsPanel.vue';
import { navigateToAppSurface } from '../../lib/app-surface-route';
import { useShellStore } from '../../stores/shell';

type SettingsSection = 'voice' | 'runtime' | 'app';

const shell = useShellStore();
const activeSection = ref<SettingsSection>('voice');

const sections = [
  { id: 'voice' as const, label: 'Voice & presence', hint: 'VAXON persona, narration, privacy', mark: '01' },
  { id: 'runtime' as const, label: 'CLI runtime', hint: 'Cursor & Codex host auth', mark: '02' },
  { id: 'app' as const, label: 'App & console', hint: 'Layout, workspace, diagnostics', mark: '03' },
];

const sectionMeta = computed(() => {
  switch (activeSection.value) {
    case 'runtime':
      return {
        title: 'CLI runtime auth',
        subtitle: 'Sign in or out of host CLI runtimes used by Agent dispatch.',
      };
    case 'app':
      return {
        title: 'App & console',
        subtitle: 'Layout mode, workspace context, and control-plane diagnostics.',
      };
    default:
      return {
        title: 'Voice & presence',
        subtitle: 'VAXON narration, hands-free voice, privacy, and mobile layout.',
      };
  }
});

const syncStatus = computed(() => {
  if (shell.operatorPresenceSettingsSaving) {
    return { tone: 'pending' as const, label: 'Saving changes…' };
  }
  if (shell.operatorPresenceSettingsError) {
    return { tone: 'error' as const, label: shell.operatorPresenceSettingsError };
  }
  if (shell.operatorPresenceSettingsSavedAt) {
    const savedAt = new Date(shell.operatorPresenceSettingsSavedAt);
    const time = savedAt.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    return { tone: 'ok' as const, label: `Saved at ${time}` };
  }
  return { tone: 'idle' as const, label: 'Synced with control plane' };
});

onMounted(() => {
  void shell.loadOperatorPresenceSettings({ reportError: true });
});

function returnToConsole(): void {
  navigateToAppSurface('console');
}
</script>

<template>
  <section class="region region-center-workbench settings-surface" aria-label="Axon-X settings">
    <div class="settings-surface__shell hud-panel-frame">
      <header class="settings-surface__header">
        <div>
          <p class="settings-surface__eyebrow">Axon-X operator</p>
          <h1 class="settings-surface__title">Settings</h1>
        </div>
        <button type="button" class="settings-surface__back" @click="returnToConsole">
          ← Console
        </button>
      </header>

      <div class="settings-surface__layout">
        <nav class="settings-surface__nav" aria-label="Settings sections">
          <button
            v-for="section in sections"
            :key="section.id"
            type="button"
            class="settings-surface__nav-button"
            :class="{ 'settings-surface__nav-button--active': activeSection === section.id }"
            @click="activeSection = section.id"
          >
            <span class="settings-surface__nav-mark">{{ section.mark }}</span>
            <span class="settings-surface__nav-copy">
              <span class="settings-surface__nav-label">{{ section.label }}</span>
              <span class="settings-surface__nav-hint">{{ section.hint }}</span>
            </span>
          </button>
        </nav>

        <div class="settings-surface__content">
          <header class="settings-surface__section-head">
            <div>
              <h2 class="settings-surface__section-title">{{ sectionMeta.title }}</h2>
              <p class="settings-surface__section-subtitle">{{ sectionMeta.subtitle }}</p>
            </div>
          </header>

          <div class="settings-surface__panel">
            <p
              v-if="activeSection === 'voice'"
              class="settings-feedback-banner settings-feedback-banner--inline"
              :class="{
                'settings-feedback-banner--error': syncStatus.tone === 'error',
                'settings-feedback-banner--ok': syncStatus.tone === 'ok',
                'settings-feedback-banner--pending': syncStatus.tone === 'pending',
              }"
              role="status"
              aria-live="polite"
            >
              {{ syncStatus.label }}
            </p>

            <OperatorPresenceSettingsForm
              v-if="activeSection === 'voice'"
              :settings="shell.operatorPresenceSettings"
              :saving="shell.operatorPresenceSettingsSaving"
              @save="shell.saveOperatorPresenceSettingsPatch($event)"
              @reset="shell.resetOperatorPresenceSettings()"
            />

            <RuntimeAuthSettingsPanel v-else-if="activeSection === 'runtime'" />
            <AppGeneralSettingsPanel v-else />
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

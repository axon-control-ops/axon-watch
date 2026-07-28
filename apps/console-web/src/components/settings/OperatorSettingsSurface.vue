<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue';

import AgentFleetControlPanel from './AgentFleetControlPanel.vue';
import AppGeneralSettingsPanel from './AppGeneralSettingsPanel.vue';
import EmailSettingsPanel from './EmailSettingsPanel.vue';
import OperatorPresenceSettingsForm from './OperatorPresenceSettingsForm.vue';
import RuntimeAuthSettingsPanel from './RuntimeAuthSettingsPanel.vue';
import type { OperatorPresenceSettings } from '../../contracts/canonical';
import { navigateToAppSurface } from '../../lib/app-surface-route';
import {
  readSettingsSectionHash,
  SETTINGS_SECTION_EVENT,
  writeSettingsSectionHash,
  type SettingsSection,
} from '../../lib/settings-section-route';
import { useShellStore } from '../../stores/shell';

const shell = useShellStore();
const activeSection = ref<SettingsSection>(readSettingsSectionHash() ?? 'voice');
const presenceFormRef = ref<{
  flushIfDirty: () => Promise<boolean>;
  dirty: { value: boolean };
} | null>(null);
const presenceDirty = ref(false);

const sections = [
  { id: 'voice' as const, label: 'Voice & presence', hint: 'VAXON persona, narration, privacy', mark: '01' },
  { id: 'agents' as const, label: 'Agents', hint: 'Autonomy mode, concurrency, stop', mark: '02' },
  { id: 'runtime' as const, label: 'CLI runtime', hint: 'Cursor & Codex host auth', mark: '03' },
  { id: 'email' as const, label: 'Email & triage', hint: 'IMAP mailboxes, bridge, inbox', mark: '04' },
  { id: 'app' as const, label: 'App & console', hint: 'Layout, workspace, diagnostics', mark: '05' },
];

const sectionMeta = computed(() => {
  switch (activeSection.value) {
    case 'agents':
      return {
        title: 'Agent fleet',
        subtitle: 'Manual, Semi, or Full autonomy — plus concurrency caps and emergency stop.',
      };
    case 'runtime':
      return {
        title: 'CLI runtime auth',
        subtitle: 'Sign in or out of host CLI runtimes used by Agent dispatch.',
      };
    case 'email':
      return {
        title: 'Email & triage',
        subtitle: 'Inbound IMAP/SMTP mailboxes, Signal bridge, and Attention routing.',
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
  if (presenceDirty.value) {
    return {
      tone: 'pending' as const,
      label: 'Unsaved changes — Save, or leave Settings to auto-save',
    };
  }
  if (shell.operatorPresenceSettingsSavedAt) {
    const savedAt = new Date(shell.operatorPresenceSettingsSavedAt);
    const time = savedAt.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    return { tone: 'ok' as const, label: `Saved at ${time}` };
  }
  return { tone: 'idle' as const, label: 'Synced with control plane' };
});

function syncSectionFromHash(): void {
  const fromHash = readSettingsSectionHash();
  if (fromHash && fromHash !== activeSection.value) {
    activeSection.value = fromHash;
  }
}

onMounted(() => {
  syncSectionFromHash();
  writeSettingsSectionHash(activeSection.value);
  window.addEventListener('popstate', syncSectionFromHash);
  window.addEventListener(SETTINGS_SECTION_EVENT, syncSectionFromHash);
  void shell.loadOperatorPresenceSettings({ reportError: true });
});

watch(activeSection, (section) => {
  writeSettingsSectionHash(section);
});

onBeforeUnmount(() => {
  window.removeEventListener('popstate', syncSectionFromHash);
  window.removeEventListener(SETTINGS_SECTION_EVENT, syncSectionFromHash);
  void presenceFormRef.value?.flushIfDirty();
});

async function persistPresenceSettings(settings: OperatorPresenceSettings): Promise<void> {
  await shell.saveOperatorPresenceSettingsPatch(settings);
}

async function leaveVoiceSectionIfNeeded(next: SettingsSection): Promise<void> {
  if (activeSection.value === 'voice' && next !== 'voice') {
    await presenceFormRef.value?.flushIfDirty();
  }
  activeSection.value = next;
}

async function returnToConsole(): Promise<void> {
  await presenceFormRef.value?.flushIfDirty();
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
            :aria-current="activeSection === section.id ? 'page' : undefined"
            @click="leaveVoiceSectionIfNeeded(section.id)"
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
              ref="presenceFormRef"
              :settings="shell.operatorPresenceSettings"
              :saving="shell.operatorPresenceSettingsSaving"
              :persist="persistPresenceSettings"
              @dirty="presenceDirty = $event"
            />

            <AgentFleetControlPanel v-else-if="activeSection === 'agents'" />
            <RuntimeAuthSettingsPanel v-else-if="activeSection === 'runtime'" />
            <EmailSettingsPanel v-else-if="activeSection === 'email'" />
            <AppGeneralSettingsPanel v-else />
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

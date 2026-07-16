<script setup lang="ts">
import type { ComposerMode } from '../../../composables/useAgentDockComposer';
import { MODE_OPTIONS } from '../../../composables/useAgentDockComposer';
import { agentExecutionAccessHint } from '../../../lib/agent-execution-access-prefs';
import { composerAccessMenuStatus } from '../../../lib/sandbox-session-view';
import PersonaTitle from '../../PersonaTitle.vue';
import { useShellStore } from '../../../stores/shell';
import { computed } from 'vue';

const props = defineProps<{
  showModeMenu: boolean;
  composerMode: ComposerMode;
  modeOptions: typeof MODE_OPTIONS;
  modeButtonLabel: string;
  modeButtonTitle: string;
  activeMode: (typeof MODE_OPTIONS)[number];
  isFullAccessAgent: boolean;
  executionAccessHint: string;
  sandboxSessionEnabled: boolean;
  sandboxEnvForced: boolean;
  sandboxHint: string;
  sandboxLabel: string;
  sandboxSessionPending?: boolean;
}>();

const emit = defineEmits<{
  'toggle-section': [];
  'select-mode': [mode: ComposerMode];
  'request-full-access': [];
  'switch-consultative': [];
  'request-sandbox-session': [];
  'disable-sandbox-session': [];
}>();

const shell = useShellStore();

const menuStatus = computed(() =>
  composerAccessMenuStatus({
    fullAccess: props.isFullAccessAgent,
    sandboxEnabled: props.sandboxSessionEnabled,
  }),
);
</script>

<template>
  <div class="agent-dock-composer__tool-group">
    <button
      type="button"
      class="agent-dock-composer__tool agent-dock-composer__tool--mode"
      :class="{
        'is-active': showModeMenu,
        'agent-dock-composer__tool--mode-full-access':
          isFullAccessAgent && !sandboxSessionEnabled,
        'agent-dock-composer__tool--mode-sandbox':
          sandboxSessionEnabled && !isFullAccessAgent,
        'agent-dock-composer__tool--mode-sandbox-full':
          sandboxSessionEnabled && isFullAccessAgent,
      }"
      :data-mode="composerMode"
      :title="modeButtonTitle"
      :aria-label="`Conversation mode: ${modeButtonLabel}`"
      @click="emit('toggle-section')"
    >
      <span class="agent-dock-composer__tool-icon" aria-hidden="true">{{ activeMode.icon }}</span>
      <span class="agent-dock-composer__tool-label agent-dock-composer__mode-chip">
        <template v-if="composerMode === 'kairo'">
          <PersonaTitle mark-size="xs" />
        </template>
        <template v-else>{{ activeMode.label }}</template>
        <span
          v-if="sandboxSessionEnabled"
          class="agent-dock-composer__mode-pill agent-dock-composer__mode-pill--sandbox"
        >Sandbox</span>
        <span
          v-if="isFullAccessAgent"
          class="agent-dock-composer__mode-pill agent-dock-composer__mode-pill--full"
        >Full</span>
      </span>
      <span class="agent-dock-composer__tool-chevron" aria-hidden="true">▾</span>
    </button>
    <div v-if="showModeMenu" class="agent-dock-composer__menu">
      <p class="agent-dock-composer__menu-caption">Conversation mode</p>
      <button
        v-for="option in modeOptions"
        :key="option.key"
        type="button"
        class="agent-dock-composer__menu-item"
        :class="{ 'is-active': composerMode === option.key }"
        @click="emit('select-mode', option.key)"
      >
        <span class="agent-dock-composer__menu-item-label">
          <PersonaTitle v-if="option.key === 'kairo'" mark-size="xs" />
          <template v-else>{{ option.icon }} {{ option.label }}</template>
        </span>
        <small>{{ option.hint }}</small>
      </button>
      <template v-if="composerMode === 'agent' || composerMode === 'debug'">
        <p class="agent-dock-composer__menu-caption">Execution access</p>
        <div
          class="agent-dock-composer__access-status"
          :class="{
            'agent-dock-composer__access-status--full': isFullAccessAgent,
            'agent-dock-composer__access-status--consultative': !isFullAccessAgent,
          }"
        >
          <span class="agent-dock-composer__access-status-dot" aria-hidden="true" />
          <span>{{ menuStatus.executionLine }}</span>
        </div>
        <button
          type="button"
          class="agent-dock-composer__menu-item"
          :class="{ 'is-active': shell.agentExecutionAccess === 'consultative' }"
          @click="emit('switch-consultative')"
        >
          <span>◌ Consultative</span>
          <small>{{ agentExecutionAccessHint('consultative') }}</small>
        </button>
        <button
          type="button"
          class="agent-dock-composer__menu-item agent-dock-composer__menu-item--full-access"
          :class="{ 'is-active': shell.agentExecutionAccess === 'full' }"
          @click="emit('request-full-access')"
        >
          <span>⬡ Full Access</span>
          <small>{{ agentExecutionAccessHint('full') }}</small>
        </button>
      </template>
      <p class="agent-dock-composer__menu-caption">Sandbox session</p>
      <div
        class="agent-dock-composer__access-status"
        :class="{
          'agent-dock-composer__access-status--sandbox': sandboxSessionEnabled,
          'agent-dock-composer__access-status--off': !sandboxSessionEnabled,
        }"
      >
        <span class="agent-dock-composer__access-status-dot" aria-hidden="true" />
        <span>{{ menuStatus.sandboxLine }}</span>
      </div>
      <button
        v-if="!sandboxSessionEnabled"
        type="button"
        class="agent-dock-composer__menu-item agent-dock-composer__menu-item--sandbox"
        :disabled="sandboxSessionPending"
        @click="emit('request-sandbox-session')"
      >
        <span>▣ Enable Sandbox</span>
        <small>{{ sandboxHint }}</small>
      </button>
      <button
        v-else
        type="button"
        class="agent-dock-composer__menu-item agent-dock-composer__menu-item--sandbox is-active"
        :disabled="sandboxEnvForced || sandboxSessionPending"
        :title="sandboxEnvForced ? sandboxHint : 'Turn Sandbox off for this session'"
        @click="emit('disable-sandbox-session')"
      >
        <span>{{ sandboxLabel }}</span>
        <small>{{ sandboxHint }}</small>
      </button>
    </div>
  </div>
</template>

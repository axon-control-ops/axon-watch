<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';

import { fetchReadiness, type ReadinessSnapshot } from '../../api/control-plane';
import { navigateToAppSurface } from '../../lib/app-surface-route';
import { useShellStore } from '../../stores/shell';

const shell = useShellStore();
const readiness = ref<ReadinessSnapshot | null>(null);
const readinessError = ref<string | null>(null);

const defaultRuntime = computed(() => shell.runtimeStatus?.default_runtime ?? '—');
const workspaceLabel = computed(
  () => shell.currentWorkspace?.display_name ?? shell.currentWorkspace?.workspace_id ?? '—',
);

onMounted(() => {
  void Promise.all([
    shell.loadRuntimeStatus(true),
    fetchReadiness()
      .then((snapshot) => {
        readiness.value = snapshot;
        readinessError.value = null;
      })
      .catch((error) => {
        readinessError.value =
          error instanceof Error ? error.message : 'Could not load control-plane readiness.';
      }),
  ]);
});
</script>

<template>
  <div class="app-general-settings">
    <section class="operator-settings-form__section">
      <header class="operator-settings-form__section-header">
        <h2>Layout mode</h2>
        <p>Switch between operator mission control and IDE workspace surfaces.</p>
      </header>
      <div class="app-general-settings__layout-toggle layout-toggle layout-toggle--mockup">
        <button
          type="button"
          class="layout-toggle__button"
          :class="{ 'layout-toggle__button--active': shell.layoutMode === 'operator' }"
          @click="shell.setLayoutMode('operator')"
        >
          Operator
        </button>
        <button
          type="button"
          class="layout-toggle__button"
          :class="{ 'layout-toggle__button--active': shell.layoutMode === 'ide' }"
          @click="shell.setLayoutMode('ide')"
        >
          IDE
        </button>
      </div>
    </section>

    <section class="operator-settings-form__section">
      <header class="operator-settings-form__section-header">
        <h2>Workspace &amp; runtime</h2>
        <p>Current operator context and default CLI dispatch target.</p>
      </header>
      <dl class="operator-settings-form__status-grid">
        <div>
          <dt>Active workspace</dt>
          <dd>{{ workspaceLabel }}</dd>
        </div>
        <div>
          <dt>Default runtime</dt>
          <dd>{{ defaultRuntime }}</dd>
        </div>
        <div>
          <dt>Composer model</dt>
          <dd>{{ shell.selectedComposerModel || 'Auto' }}</dd>
        </div>
      </dl>
    </section>

    <section class="operator-settings-form__section">
      <header class="operator-settings-form__section-header">
        <h2>Control plane</h2>
        <p>Live bootstrap readiness from the Axon-X control plane.</p>
      </header>
      <dl class="operator-settings-form__status-grid">
        <div>
          <dt>Service</dt>
          <dd>{{ readiness?.service ?? '—' }}</dd>
        </div>
        <div>
          <dt>Status</dt>
          <dd>{{ readiness?.status ?? (readinessError ? 'Unavailable' : 'Loading…') }}</dd>
        </div>
        <div>
          <dt>Deployment mode</dt>
          <dd>{{ readiness?.mode ?? '—' }}</dd>
        </div>
        <div>
          <dt>State dir</dt>
          <dd>{{ readiness?.state_dir ?? '—' }}</dd>
        </div>
      </dl>
      <p v-if="readinessError" class="operator-settings-form__status-note" role="alert">
        {{ readinessError }}
      </p>
    </section>

    <section class="operator-settings-form__section">
      <header class="operator-settings-form__section-header">
        <h2>Related surfaces</h2>
        <p>Jump to other Axon-X foundation pages.</p>
      </header>
      <div class="app-general-settings__links">
        <button type="button" class="operator-settings-form__button" @click="navigateToAppSurface('vault')">
          Open Vault
        </button>
        <button type="button" class="operator-settings-form__button operator-settings-form__button--ghost" @click="navigateToAppSurface('data')">
          Open Data
        </button>
        <button type="button" class="operator-settings-form__button operator-settings-form__button--ghost" @click="navigateToAppSurface('console')">
          Back to console
        </button>
      </div>
    </section>
  </div>
</template>

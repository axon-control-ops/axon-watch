<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';

import { fetchTunnelStatus } from '../../api/control-plane';
import KairoConversationBar from '../../features/kairo-conversation/KairoConversationBar.vue';
import KairoGalaxyOrbSvg from '../../features/brain-galaxy/KairoGalaxyOrbSvg.vue';
import { navigateToAppSurface } from '../../lib/app-surface-route';
import { mobileTunnelActionState } from '../../lib/mobile-tunnel-view';
import { useShellStore } from '../../stores/shell';

const shell = useShellStore();
const tunnelUrl = ref<string | null>(null);
const tunnelLoadState = ref<'loading' | 'loaded' | 'error'>('loading');
const tunnelActionError = ref<string | null>(null);

async function refreshTunnelStatus(): Promise<void> {
  tunnelLoadState.value = 'loading';
  tunnelActionError.value = null;
  try {
    const status = await fetchTunnelStatus();
    tunnelUrl.value = status.url?.trim() || null;
    tunnelLoadState.value = 'loaded';
  } catch (error) {
    tunnelUrl.value = null;
    tunnelLoadState.value = 'error';
    tunnelActionError.value =
      error instanceof Error ? error.message : 'Tunnel status is unavailable.';
  }
}

async function setTunnelRunning(running: boolean): Promise<void> {
  tunnelActionError.value = null;
  if (running) {
    await shell.startCloudflareTunnel();
  } else {
    await shell.stopCloudflareTunnel();
  }
  if (shell.connectorsError) {
    tunnelActionError.value = shell.connectorsError;
  }
  await refreshTunnelStatus();
}

onMounted(() => {
  if (shell.briefingLoadState === 'idle') {
    void shell.loadOperatorBriefing();
  }
  if (shell.operatorFleetHealthLoadState === 'idle') {
    void shell.loadOperatorFleetHealth();
  }
  void refreshTunnelStatus();
});

const briefing = computed(() => shell.operatorBriefing);
const fleetItems = computed(() => shell.operatorFleetHealth?.items.slice(0, 4) ?? []);
const tunnelActions = computed(() =>
  mobileTunnelActionState({
    url: tunnelUrl.value,
    loading: tunnelLoadState.value === 'loading',
    mutationPending: shell.connectorMutationPending,
  }),
);
</script>

<template>
  <main class="operator-mobile-shell" aria-label="KAIRO mobile operator shell">
    <header class="operator-mobile-shell__header">
      <div>
        <p class="operator-mobile-shell__eyebrow">KAIRO remote</p>
        <h1 class="operator-mobile-shell__title">Operator shell</h1>
      </div>
      <button type="button" class="operator-mobile-shell__link" @click="navigateToAppSurface('console')">
        Full console
      </button>
    </header>

    <section class="operator-mobile-shell__briefing">
      <p class="operator-mobile-shell__notice">{{ briefing?.notice ?? 'Loading briefing…' }}</p>
      <p class="operator-mobile-shell__advise">{{ briefing?.advise ?? '' }}</p>
    </section>

    <section v-if="fleetItems.length" class="operator-mobile-shell__fleet" aria-label="Fleet health">
      <h2 class="operator-mobile-shell__section-title">Fleet</h2>
      <ul class="operator-mobile-shell__fleet-list">
        <li
          v-for="item in fleetItems"
          :key="item.workspace_id"
          class="operator-mobile-shell__fleet-item"
          :class="`operator-mobile-shell__fleet-item--${item.health}`"
        >
          <strong>{{ item.display_name }}</strong>
          <span>{{ item.open_signals_count }} signals · {{ item.active_runs }} runs</span>
        </li>
      </ul>
    </section>

    <section class="operator-mobile-shell__voice">
      <div class="operator-mobile-shell__voice-orb" aria-hidden="true">
        <KairoGalaxyOrbSvg />
      </div>
      <KairoConversationBar />
    </section>

    <section class="operator-mobile-shell__tunnel">
      <h2 class="operator-mobile-shell__section-title">Tunnel</h2>
      <p v-if="tunnelUrl" class="operator-mobile-shell__tunnel-copy">
        Remote URL:
        <a :href="tunnelUrl" target="_blank" rel="noreferrer">{{ tunnelUrl }}</a>
      </p>
      <p v-else class="operator-mobile-shell__tunnel-copy">
        {{
          tunnelLoadState === 'loading'
            ? 'Checking tunnel status…'
            : 'Start the Cloudflare tunnel to reach this shell remotely.'
        }}
      </p>
      <div class="operator-mobile-shell__tunnel-actions">
        <button
          type="button"
          class="operator-mobile-shell__action"
          :disabled="tunnelActions.startDisabled"
          :title="tunnelActions.running ? 'Tunnel is already running' : 'Start Cloudflare tunnel'"
          @click="setTunnelRunning(true)"
        >
          {{
            shell.connectorMutationPending && !tunnelActions.running
              ? 'Starting…'
              : 'Start tunnel'
          }}
        </button>
        <button
          type="button"
          class="operator-mobile-shell__action operator-mobile-shell__action--ghost"
          :disabled="tunnelActions.stopDisabled"
          :title="tunnelActions.running ? 'Stop Cloudflare tunnel' : 'No tunnel is running'"
          @click="setTunnelRunning(false)"
        >
          {{ shell.connectorMutationPending && tunnelActions.running ? 'Stopping…' : 'Stop' }}
        </button>
      </div>
      <p v-if="tunnelActionError" class="operator-mobile-shell__tunnel-error" role="alert">
        {{ tunnelActionError }}
      </p>
    </section>
  </main>
</template>

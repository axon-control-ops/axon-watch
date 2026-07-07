<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';

import { fetchTunnelStatus } from '../../api/control-plane';
import KairoConversationBar from '../../features/kairo-conversation/KairoConversationBar.vue';
import KairoGalaxyOrb from '../../features/brain-galaxy/KairoGalaxyOrb.vue';
import { navigateToAppSurface } from '../../lib/app-surface-route';
import { useShellStore } from '../../stores/shell';

const shell = useShellStore();
const tunnelUrl = ref<string | null>(null);

onMounted(() => {
  if (shell.briefingLoadState === 'idle') {
    void shell.loadOperatorBriefing();
  }
  if (shell.operatorFleetHealthLoadState === 'idle') {
    void shell.loadOperatorFleetHealth();
  }
  void fetchTunnelStatus()
    .then((status) => {
      tunnelUrl.value = status.url?.trim() || null;
    })
    .catch(() => {
      tunnelUrl.value = null;
    });
});

const briefing = computed(() => shell.operatorBriefing);
const fleetItems = computed(() => shell.operatorFleetHealth?.items.slice(0, 4) ?? []);
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
      <KairoGalaxyOrb />
      <KairoConversationBar />
    </section>

    <section class="operator-mobile-shell__tunnel">
      <h2 class="operator-mobile-shell__section-title">Tunnel</h2>
      <p v-if="tunnelUrl" class="operator-mobile-shell__tunnel-copy">
        Remote URL:
        <a :href="tunnelUrl" target="_blank" rel="noreferrer">{{ tunnelUrl }}</a>
      </p>
      <p v-else class="operator-mobile-shell__tunnel-copy">
        Start the Cloudflare tunnel from Connectors in the full console to reach this shell remotely.
      </p>
      <div class="operator-mobile-shell__tunnel-actions">
        <button
          type="button"
          class="operator-mobile-shell__action"
          :disabled="shell.connectorMutationPending"
          @click="shell.startCloudflareTunnel()"
        >
          Start tunnel
        </button>
        <button
          type="button"
          class="operator-mobile-shell__action operator-mobile-shell__action--ghost"
          :disabled="shell.connectorMutationPending"
          @click="shell.stopCloudflareTunnel()"
        >
          Stop
        </button>
      </div>
    </section>
  </main>
</template>

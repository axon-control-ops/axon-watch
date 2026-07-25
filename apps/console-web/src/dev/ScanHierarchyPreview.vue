<script setup lang="ts">
const scanOrder = [
  {
    rank: 1,
    region: 'Topbar',
    purpose: 'Global runtime truth at a glance',
    elements: ['Brand', 'Workspace trail', 'Run / watch / degraded chips', 'KAIRO chip', 'Mode toggle'],
  },
  {
    rank: 2,
    region: 'Right dock hero',
    purpose: 'Active exception and KAIRO briefing',
    elements: ['KAIRO Briefing (Operator hero)', 'Approvals', 'Signals', 'Active Run'],
  },
  {
    rank: 3,
    region: 'Center workbench',
    purpose: 'Evidence and action surface',
    elements: ['Editor', 'Preview', 'Workspace documents'],
  },
  {
    rank: 4,
    region: 'Bottom panel',
    purpose: 'Terminal and runtime detail',
    elements: ['Terminal', 'Runtime summary'],
  },
  {
    rank: 5,
    region: 'Status bar',
    purpose: 'Persistent short truth strip',
    elements: ['Mode', 'Workspace', 'Watch', 'Signals count', 'Approvals count', 'Degraded reason'],
  },
];
</script>

<template>
  <div class="scan-preview">
    <header class="scan-preview__header">
      <p class="eyebrow">AXON-X UX-0</p>
      <h1>Scan hierarchy preview</h1>
      <p class="region-copy">
        Operator scan order for the JARVIS-forward shell. This page documents UX-0 region ownership
        and is available in dev via <code>?scan-preview=1</code>.
      </p>
      <a class="scan-preview__back" href="/">Back to console</a>
    </header>

    <ol class="scan-preview__list">
      <li v-for="item in scanOrder" :key="item.rank" class="scan-preview__item">
        <div class="scan-preview__rank">{{ item.rank }}</div>
        <div>
          <h2>{{ item.region }}</h2>
          <p class="region-copy">{{ item.purpose }}</p>
          <ul class="scan-preview__elements">
            <li v-for="element in item.elements" :key="element">{{ element }}</li>
          </ul>
        </div>
      </li>
    </ol>
  </div>
</template>

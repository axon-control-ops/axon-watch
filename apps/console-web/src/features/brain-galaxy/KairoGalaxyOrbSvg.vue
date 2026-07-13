<script setup lang="ts">
import { galaxyOrbBeads, galaxyOrbTicks } from './kairo-galaxy-orb-view';

defineProps<{
  personaOrbLabel: string;
}>();

const ticks = galaxyOrbTicks();
const beads = galaxyOrbBeads();
</script>

<template>
  <svg class="kairo-galaxy-orb__svg" viewBox="0 0 200 200" role="img" aria-hidden="true">
    <defs>
      <radialGradient id="kairo-orb-core-glow" cx="50%" cy="50%" r="50%">
        <stop offset="0%" stop-color="rgba(72, 196, 255, 0.38)" />
        <stop offset="100%" stop-color="rgba(72, 196, 255, 0)" />
      </radialGradient>
      <radialGradient id="kairo-orb-handsfree-glow" cx="50%" cy="50%" r="50%">
        <stop offset="0%" stop-color="rgba(92, 255, 180, 0.42)" />
        <stop offset="100%" stop-color="rgba(92, 255, 180, 0)" />
      </radialGradient>
      <linearGradient
        id="kairo-orb-persona-grad"
        x1="4"
        y1="4"
        x2="20"
        y2="20"
        gradientUnits="userSpaceOnUse"
      >
        <stop stop-color="#9ef0ff" />
        <stop offset="0.45" stop-color="#48c4ff" />
        <stop offset="1" stop-color="#e8fbff" />
      </linearGradient>
      <filter id="kairo-orb-glow" x="-40%" y="-40%" width="180%" height="180%">
        <feGaussianBlur stdDeviation="3.2" result="blur" />
        <feMerge>
          <feMergeNode in="blur" />
          <feMergeNode in="SourceGraphic" />
        </feMerge>
      </filter>
    </defs>

    <circle class="kairo-galaxy-orb__halo" cx="100" cy="100" r="92" fill="url(#kairo-orb-core-glow)" />

    <g class="kairo-galaxy-orb__ticks">
      <line
        v-for="(tick, index) in ticks"
        :key="index"
        :x1="tick.x1"
        :y1="tick.y1"
        :x2="tick.x2"
        :y2="tick.y2"
        :class="{ 'kairo-galaxy-orb__tick--major': tick.major }"
      />
    </g>

    <circle class="kairo-galaxy-orb__ring kairo-galaxy-orb__ring--outer" cx="100" cy="100" r="72" />
    <circle class="kairo-galaxy-orb__ring kairo-galaxy-orb__ring--dashed" cx="100" cy="100" r="66" />
    <path class="kairo-galaxy-orb__arc" d="M 44 100 A 66 66 0 0 1 62 56" pathLength="100" />

    <g class="kairo-galaxy-orb__beads">
      <circle
        v-for="(bead, index) in beads"
        :key="index"
        class="kairo-galaxy-orb__bead"
        :cx="bead.cx"
        :cy="bead.cy"
        r="2.6"
      />
    </g>

    <circle class="kairo-galaxy-orb__ring kairo-galaxy-orb__ring--inner" cx="100" cy="100" r="54" />
    <circle class="kairo-galaxy-orb__ring kairo-galaxy-orb__ring--core" cx="100" cy="100" r="46" />

    <text class="kairo-galaxy-orb__core-text" x="100" y="103" filter="url(#kairo-orb-glow)">
      {{ personaOrbLabel }}
    </text>

    <circle class="kairo-galaxy-orb__beacon" cx="34" cy="34" r="4.5" filter="url(#kairo-orb-glow)" />
    <circle class="kairo-galaxy-orb__sweep" cx="100" cy="100" r="48" />
    <circle class="kairo-galaxy-orb__pulse" cx="100" cy="100" r="56" />
  </svg>
</template>

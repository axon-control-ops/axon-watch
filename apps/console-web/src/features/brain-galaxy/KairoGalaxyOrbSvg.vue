<script setup lang="ts">
import {
  galaxyOrbBeads,
  galaxyOrbGlassShards,
  galaxyOrbMeshDots,
  galaxyOrbTicks,
} from './kairo-galaxy-orb-view';

defineProps<{
  personaOrbLabel: string;
}>();

const ticks = galaxyOrbTicks();
const beads = galaxyOrbBeads();
const meshDots = galaxyOrbMeshDots();
const shards = galaxyOrbGlassShards();
</script>

<template>
  <svg class="kairo-galaxy-orb__svg" viewBox="0 0 220 220" role="img" aria-hidden="true">
    <defs>
      <radialGradient id="kairo-orb-plasma" cx="38%" cy="32%" r="62%">
        <stop offset="0%" stop-color="#ffffff" stop-opacity="0.98" />
        <stop offset="14%" stop-color="#d8fbff" stop-opacity="0.95" />
        <stop offset="36%" stop-color="#48c4ff" stop-opacity="0.88" />
        <stop offset="68%" stop-color="#0a6fa8" stop-opacity="0.78" />
        <stop offset="100%" stop-color="#021018" stop-opacity="0.94" />
      </radialGradient>
      <radialGradient id="kairo-orb-core-glow" cx="50%" cy="50%" r="50%">
        <stop offset="0%" stop-color="rgba(140, 235, 255, 0.62)" />
        <stop offset="55%" stop-color="rgba(0, 170, 255, 0.22)" />
        <stop offset="100%" stop-color="rgba(0, 120, 200, 0)" />
      </radialGradient>
      <radialGradient id="kairo-orb-bloom" cx="50%" cy="50%" r="50%">
        <stop offset="0%" stop-color="rgba(72, 196, 255, 0.42)" />
        <stop offset="100%" stop-color="rgba(72, 196, 255, 0)" />
      </radialGradient>
      <linearGradient id="kairo-orb-ring-sheen" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" stop-color="rgba(180, 245, 255, 0.95)" />
        <stop offset="45%" stop-color="rgba(72, 196, 255, 0.35)" />
        <stop offset="100%" stop-color="rgba(0, 140, 220, 0.75)" />
      </linearGradient>
      <linearGradient id="kairo-orb-shard-fill" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" stop-color="rgba(120, 220, 255, 0.35)" />
        <stop offset="55%" stop-color="rgba(40, 120, 180, 0.12)" />
        <stop offset="100%" stop-color="rgba(180, 240, 255, 0.22)" />
      </linearGradient>
      <filter id="kairo-orb-glow" x="-50%" y="-50%" width="200%" height="200%">
        <feGaussianBlur stdDeviation="2.8" result="blur" />
        <feMerge>
          <feMergeNode in="blur" />
          <feMergeNode in="SourceGraphic" />
        </feMerge>
      </filter>
      <filter id="kairo-orb-soft-bloom" x="-80%" y="-80%" width="260%" height="260%">
        <feGaussianBlur stdDeviation="7.2" result="soft" />
        <feMerge>
          <feMergeNode in="soft" />
          <feMergeNode in="SourceGraphic" />
        </feMerge>
      </filter>
    </defs>

    <!-- Outer bloom field -->
    <circle class="kairo-galaxy-orb__bloom" cx="110" cy="110" r="108" fill="url(#kairo-orb-bloom)" />
    <circle class="kairo-galaxy-orb__bloom kairo-galaxy-orb__bloom--deep" cx="110" cy="110" r="96" fill="url(#kairo-orb-bloom)" />
    <circle class="kairo-galaxy-orb__halo" cx="110" cy="110" r="96" fill="url(#kairo-orb-core-glow)" />

    <!-- Outer glass shards -->
    <g class="kairo-galaxy-orb__shards">
      <polygon
        v-for="(shard, index) in shards"
        :key="index"
        class="kairo-galaxy-orb__shard"
        :class="`kairo-galaxy-orb__shard--orbit-${shard.orbitIndex}`"
        :points="shard.points"
        :opacity="shard.opacity"
        fill="url(#kairo-orb-shard-fill)"
      />
    </g>

    <!-- Outer HUD ticks -->
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

    <!-- Concentric dials -->
    <circle class="kairo-galaxy-orb__ring kairo-galaxy-orb__ring--outer" cx="110" cy="110" r="82" />
    <circle class="kairo-galaxy-orb__ring kairo-galaxy-orb__ring--dashed" cx="110" cy="110" r="74" />
    <circle class="kairo-galaxy-orb__ring kairo-galaxy-orb__ring--mid" cx="110" cy="110" r="66" />

    <!-- Amber attention arc + beads (mockup 9–1 o'clock) -->
    <path
      class="kairo-galaxy-orb__arc"
      d="M 48 110 A 74 74 0 0 1 78 52"
      pathLength="100"
    />
    <g class="kairo-galaxy-orb__beads">
      <circle
        v-for="(bead, index) in beads"
        :key="index"
        class="kairo-galaxy-orb__bead"
        :cx="bead.cx"
        :cy="bead.cy"
        :r="bead.r"
      />
    </g>

    <!-- JARVIS mesh lattice (particle cage) -->
    <g class="kairo-galaxy-orb__mesh">
      <circle
        v-for="(dot, index) in meshDots"
        :key="index"
        class="kairo-galaxy-orb__mesh-dot"
        :class="{ 'kairo-galaxy-orb__mesh-dot--accent': dot.accent === 'pink' }"
        :cx="dot.cx"
        :cy="dot.cy"
        :r="dot.r"
        :opacity="dot.opacity"
      />
    </g>

    <!-- Equatorial elliptical rings (perspective) -->
    <ellipse
      class="kairo-galaxy-orb__ellipse kairo-galaxy-orb__ellipse--a"
      cx="110"
      cy="112"
      rx="58"
      ry="18"
      fill="none"
      stroke="url(#kairo-orb-ring-sheen)"
      stroke-width="1.4"
    />
    <ellipse
      class="kairo-galaxy-orb__ellipse kairo-galaxy-orb__ellipse--b"
      cx="110"
      cy="108"
      rx="50"
      ry="14"
      fill="none"
      stroke="url(#kairo-orb-ring-sheen)"
      stroke-width="1.1"
      opacity="0.65"
    />

    <!-- Volumetric plasma core -->
    <circle
      class="kairo-galaxy-orb__plasma"
      cx="110"
      cy="110"
      r="42"
      fill="url(#kairo-orb-plasma)"
      filter="url(#kairo-orb-soft-bloom)"
    />
    <circle class="kairo-galaxy-orb__ring kairo-galaxy-orb__ring--core" cx="110" cy="110" r="44" />
    <circle class="kairo-galaxy-orb__specular" cx="96" cy="96" r="10" />

    <text class="kairo-galaxy-orb__core-text" x="110" y="114" filter="url(#kairo-orb-glow)">
      {{ personaOrbLabel }}
    </text>

    <!-- Ready beacon (green, ~10 o'clock) -->
    <circle class="kairo-galaxy-orb__beacon" cx="58" cy="52" r="4.2" filter="url(#kairo-orb-glow)" />
    <circle class="kairo-galaxy-orb__sweep" cx="110" cy="110" r="52" />
    <circle class="kairo-galaxy-orb__pulse" cx="110" cy="110" r="60" />
  </svg>
</template>

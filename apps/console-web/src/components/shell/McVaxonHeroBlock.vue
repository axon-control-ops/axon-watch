<script setup lang="ts">
import KairoGalaxyOrb from '../../features/brain-galaxy/KairoGalaxyOrb.vue';
import MissionControlAutonomyControl from './MissionControlAutonomyControl.vue';
import { useShellStore } from '../../stores/shell';

defineProps<{
  modeChip: string;
  fullAutonomyActive: boolean;
  autonomyMode: string;
  /** Tall rail layout for operator right dock. */
  dockRail?: boolean;
}>();

const shell = useShellStore();
</script>

<template>
  <div
    class="mc-vaxon-hero"
    :class="{ 'mc-vaxon-hero--dock-rail': dockRail }"
  >
    <div
      class="mc-live-ops__orb-stage mc-vaxon-hero__orb"
      :data-speaking="shell.kairoSpeechActive ? 'true' : 'false'"
      :data-mode="modeChip"
      :data-autonomy="fullAutonomyActive ? 'armed' : autonomyMode"
    >
      <div class="mc-live-ops__orb-visual mc-vaxon-hero__orb-visual">
        <KairoGalaxyOrb placement-mode="embedded" />
        <MissionControlAutonomyControl />
      </div>
    </div>

    <div
      class="mc-live-ops__modes mc-vaxon-hero__modes"
      role="status"
      aria-label="Voice mode"
    >
      <span class="mc-live-ops__mode" :data-active="modeChip === 'speaking' ? 'true' : 'false'">Speaking</span>
      <span class="mc-live-ops__mode" :data-active="modeChip === 'listening' ? 'true' : 'false'">Listening</span>
      <span class="mc-live-ops__mode" :data-active="modeChip === 'autonomous' ? 'true' : 'false'">Autonomous</span>
      <span class="mc-live-ops__mode" :data-active="modeChip === 'scanning' ? 'true' : 'false'">Scanning</span>
      <span class="mc-live-ops__mode" :data-active="modeChip === 'standby' ? 'true' : 'false'">Standby</span>
    </div>
  </div>
</template>

<style scoped src="./mission-control-live-ops.css"></style>
<style scoped>
.mc-vaxon-hero {
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
  min-height: 0;
}

.mc-vaxon-hero--dock-rail {
  flex: 1 1 auto;
  min-height: 18rem;
}

.mc-vaxon-hero--dock-rail .mc-vaxon-hero__orb {
  flex: 1 1 auto;
  min-height: 15rem;
  max-height: none;
  margin: 0;
  overflow: visible;
}

.mc-vaxon-hero--dock-rail .mc-vaxon-hero__orb-visual {
  display: flex;
  align-items: center;
  justify-content: center;
  flex: 1 1 auto;
  min-height: 14.5rem;
  padding: 0.65rem 0.35rem 3.35rem;
  overflow: visible;
}

.mc-vaxon-hero--dock-rail :deep(.brain-galaxy-stage__jarvis-float--embedded) {
  width: min(100%, 16.5rem);
  margin: 0 auto;
}

.mc-vaxon-hero--dock-rail :deep(.kairo-galaxy-orb__trigger) {
  width: min(100%, 16.5rem);
  height: min(100%, 16.5rem);
  max-width: 100%;
  aspect-ratio: 1;
}

.mc-vaxon-hero__orb-visual :deep(.brain-galaxy-stage__jarvis-float--embedded) {
  position: relative;
  inset: auto;
  transform: none;
  pointer-events: auto;
  z-index: 1;
}

.mc-vaxon-hero__orb-visual :deep(.kairo-galaxy-orb__trigger) {
  width: min(72vw, 16rem);
  height: min(72vw, 16rem);
  max-width: 100%;
}

.mc-vaxon-hero__modes {
  flex-shrink: 0;
  grid-template-columns: repeat(5, minmax(0, 1fr));
}
</style>

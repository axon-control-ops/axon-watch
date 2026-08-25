<script setup lang="ts">
import { useShellStore } from '../../stores/shell';
import OperatorPersonaMark from '../OperatorPersonaMark.vue';

const shell = useShellStore();

function title(): string {
  if (shell.ideBriefingPanelOpen || shell.ideVaxonDockPinned) {
    return shell.ideVaxonDockPinned && shell.ideActivityView === 'team'
      ? 'VAXON talk · Click to close'
      : 'VAXON briefing · Click to close';
  }
  if (shell.kairoSpeechActive) return 'VAXON is speaking · Open briefing';
  if (shell.showKairoBriefingAttention) {
    return `${shell.kairoBriefingAttentionLabel} · Open VAXON briefing`;
  }
  return 'Talk to VAXON · Open briefing';
}

function ariaLabel(): string {
  return shell.ideBriefingPanelOpen || shell.ideVaxonDockPinned
    ? 'Close VAXON briefing panel'
    : 'Open VAXON briefing to talk or listen';
}

function toggle(): void {
  if (shell.ideBriefingPanelOpen || shell.ideVaxonDockPinned) {
    shell.closeIdeBriefingPanel();
    return;
  }
  shell.focusKairoBriefing();
}
</script>

<template>
  <button
    type="button"
    class="ide-activity-bar__button ide-activity-bar__button--vaxon"
    :class="{
      'ide-activity-bar__button--active': shell.ideBriefingPanelOpen || shell.ideVaxonDockPinned,
      'ide-activity-bar__button--vaxon-speaking': shell.kairoSpeechActive,
      'ide-activity-bar__button--vaxon-attention':
        shell.showKairoBriefingAttention && !shell.ideBriefingPanelOpen && !shell.ideVaxonDockPinned,
    }"
    :aria-label="ariaLabel()"
    :aria-pressed="shell.ideBriefingPanelOpen || shell.ideVaxonDockPinned"
    :title="title()"
    @click="toggle"
  >
    <OperatorPersonaMark size="sm" class="ide-activity-bar__vaxon-mark" />
    <span
      v-if="shell.showKairoBriefingAttention && !shell.ideBriefingPanelOpen && !shell.ideVaxonDockPinned"
      class="ide-activity-bar__badge ide-activity-bar__badge--vaxon"
      aria-hidden="true"
    >
      {{ shell.kairoBriefingAttention.badgeCount }}
    </span>
    <span
      v-else-if="shell.kairoSpeechActive"
      class="ide-activity-bar__pulse ide-activity-bar__pulse--vaxon"
      aria-hidden="true"
    />
  </button>
</template>

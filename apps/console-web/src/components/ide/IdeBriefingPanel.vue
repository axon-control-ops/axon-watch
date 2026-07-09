<script setup lang="ts">
import BriefingPanel from '../BriefingPanel.vue';
import PersonaTitle from '../PersonaTitle.vue';
import { useShellStore } from '../../stores/shell';

const shell = useShellStore();

function closePanel(): void {
  shell.closeIdeBriefingPanel();
}
</script>

<template>
  <section
    id="ide-briefing-panel"
    class="ide-briefing-panel hud-panel-frame"
    aria-label="VAXON written briefing"
  >
    <div class="panel-heading ide-briefing-panel__heading">
      <p class="panel-heading__title">
        <PersonaTitle suffix="Briefing" mark-size="xs" />
      </p>
      <button
        type="button"
        class="ide-briefing-panel__close"
        aria-label="Close briefing panel"
        @click="closePanel"
      >
        ×
      </button>
    </div>
    <BriefingPanel
      class="ide-briefing-panel__body"
      :briefing="shell.operatorBriefing"
      :load-state="shell.briefingLoadState"
      :error="shell.briefingError"
      :summary-line="shell.briefingSummaryLine"
    />
  </section>
</template>

<style scoped>
.ide-briefing-panel {
  display: flex;
  flex-direction: column;
  min-height: 0;
  height: 100%;
  overflow: hidden;
}

.ide-briefing-panel__heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  flex-shrink: 0;
}

.ide-briefing-panel__close {
  border: 1px solid rgba(255, 255, 255, 0.14);
  border-radius: 0.35rem;
  background: rgba(255, 255, 255, 0.04);
  color: inherit;
  cursor: pointer;
  font: inherit;
  font-size: 1rem;
  line-height: 1;
  padding: 0.15rem 0.45rem;
}

.ide-briefing-panel__body {
  flex: 1;
  min-height: 0;
  overflow: auto;
}
</style>

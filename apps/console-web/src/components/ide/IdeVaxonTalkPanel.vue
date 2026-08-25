<script setup lang="ts">
import KairoConversationBar from '../../features/kairo-conversation/KairoConversationBar.vue';
import PersonaTitle from '../PersonaTitle.vue';
import { useShellStore } from '../../stores/shell';

const shell = useShellStore();

function closePanel(): void {
  shell.closeIdeBriefingPanel();
}
</script>

<template>
  <section
    id="ide-vaxon-talk-panel"
    class="ide-vaxon-talk-panel hud-panel-frame"
    aria-label="Talk to VAXON"
  >
    <div class="ide-vaxon-talk-panel__heading panel-heading">
      <p class="panel-heading__title">
        <PersonaTitle suffix="Voice" mark-size="xs" />
      </p>
      <button
        type="button"
        class="ide-vaxon-talk-panel__close"
        aria-label="Close VAXON talk panel"
        title="Close"
        @click="closePanel"
      >
        ×
      </button>
    </div>
    <div class="ide-vaxon-talk-panel__body">
      <KairoConversationBar />
    </div>
  </section>
</template>

<style scoped>
.ide-vaxon-talk-panel {
  display: flex;
  flex-direction: column;
  min-height: 0;
  height: 100%;
  overflow: hidden;
}

.ide-vaxon-talk-panel__heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  flex-shrink: 0;
  padding: 0.35rem 0.5rem 0.15rem;
}

.ide-vaxon-talk-panel__close {
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

.ide-vaxon-talk-panel__body {
  flex: 1;
  min-height: 0;
  overflow: auto;
  padding: 0 0.35rem 0.35rem;
}

.ide-vaxon-talk-panel__body :deep(.kairo-conversation-bar) {
  min-height: 0;
}
</style>

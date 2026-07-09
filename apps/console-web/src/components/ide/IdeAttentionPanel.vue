<script setup lang="ts">
import AttentionStackPanel from '../shell/AttentionStackPanel.vue';
import { useShellStore } from '../../stores/shell';

const shell = useShellStore();

function closePanel(): void {
  shell.closeIdeAttentionPanel();
}
</script>

<template>
  <section
    id="ide-attention-panel"
    class="ide-attention-panel hud-panel-frame"
    aria-label="IDE attention"
  >
    <div class="panel-heading ide-attention-panel__heading">
      <p class="panel-heading__title">ATTENTION</p>
      <button
        type="button"
        class="ide-attention-panel__close"
        aria-label="Close attention panel"
        @click="closePanel"
      >
        ×
      </button>
    </div>
    <AttentionStackPanel variant="sidebar" />
  </section>
</template>

<style scoped>
.ide-attention-panel {
  display: flex;
  flex-direction: column;
  min-height: 0;
  height: 100%;
  overflow: hidden;
}

.ide-attention-panel__heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  flex-shrink: 0;
}

.ide-attention-panel__close {
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
</style>

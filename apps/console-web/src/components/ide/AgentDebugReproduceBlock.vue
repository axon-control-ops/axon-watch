<script setup lang="ts">
/**
 * In-thread reproduce steps. Live Runtime logs stay in the sticky composer
 * banner so the feed is not duplicated across every historical pause card.
 */
defineProps<{
  steps: string[];
  workspaceId?: string | null;
}>();
</script>

<template>
  <section class="agent-debug-reproduce-block" aria-label="Debug reproduce steps">
    <header class="agent-debug-reproduce-block__header">
      <span class="agent-debug-reproduce-block__badge">DEBUG</span>
      <p class="agent-debug-reproduce-block__title">Reproduce · Ctrl+Enter to continue</p>
    </header>
    <ol class="agent-debug-reproduce-block__steps">
      <li v-for="(step, index) in steps" :key="index">{{ step }}</li>
    </ol>
  </section>
</template>

<style scoped>
.agent-debug-reproduce-block {
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
  margin: 0.35rem 0 0.15rem;
  padding: 0.55rem 0.65rem;
  border: 1px solid rgba(167, 139, 250, 0.38);
  border-radius: 0.35rem;
  background: rgba(46, 16, 101, 0.42);
}

.agent-debug-reproduce-block__header {
  display: flex;
  align-items: center;
  gap: 0.45rem;
}

.agent-debug-reproduce-block__badge {
  flex-shrink: 0;
  padding: 0.08rem 0.35rem;
  border-radius: 999px;
  border: 1px solid rgba(167, 139, 250, 0.5);
  font-size: 0.52rem;
  letter-spacing: 0.08em;
  font-weight: 700;
  color: rgba(221, 214, 254, 0.96);
}

.agent-debug-reproduce-block__title {
  margin: 0;
  font-size: 0.68rem;
  color: rgba(237, 233, 254, 0.95);
}

.agent-debug-reproduce-block__steps {
  margin: 0;
  padding-left: 1.1rem;
  font-size: 0.68rem;
  line-height: 1.45;
  color: rgba(237, 233, 254, 0.92);
}
</style>

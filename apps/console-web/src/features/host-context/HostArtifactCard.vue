<script setup lang="ts">
import type { HostArtifactRecord } from '../../contracts/canonical';

defineProps<{
  artifact: HostArtifactRecord;
  desktopActions?: boolean;
}>();

const emit = defineEmits<{
  open: [artifact: HostArtifactRecord];
  reveal: [artifact: HostArtifactRecord];
}>();
</script>

<template>
  <article class="host-artifact-card glass-surface glass-surface--tier-2">
    <header class="host-artifact-card__head">
      <span class="host-artifact-card__kind">{{ artifact.kind }}</span>
      <span class="host-artifact-card__when">{{ artifact.modified_at }}</span>
    </header>
    <h3 class="host-artifact-card__title">{{ artifact.title || artifact.path }}</h3>
    <p class="host-artifact-card__meta">
      {{ artifact.origin }} · {{ artifact.sensitivity }}
    </p>
    <footer v-if="desktopActions" class="host-artifact-card__actions">
      <button type="button" class="host-artifact-card__btn" @click="emit('open', artifact)">Open</button>
      <button type="button" class="host-artifact-card__btn" @click="emit('reveal', artifact)">Reveal</button>
    </footer>
  </article>
</template>

<style scoped>
.host-artifact-card {
  display: grid;
  gap: 0.35rem;
  padding: 0.7rem 0.8rem;
  border: 1px solid var(--border-glass);
  border-radius: var(--radius-shell);
}
.host-artifact-card__head {
  display: flex;
  justify-content: space-between;
  gap: 0.5rem;
  color: var(--text-muted);
  font-size: var(--font-size-caption);
}
.host-artifact-card__title {
  margin: 0;
  font-size: var(--font-size-ui);
  color: var(--text-primary);
}
.host-artifact-card__meta {
  margin: 0;
  color: var(--text-secondary);
  font-size: var(--font-size-meta);
}
.host-artifact-card__actions {
  display: flex;
  gap: 0.4rem;
}
.host-artifact-card__btn {
  appearance: none;
  border: 1px solid var(--border-glass);
  background: transparent;
  color: var(--text-hud);
  font: inherit;
  font-size: var(--font-size-caption);
  padding: 0.2rem 0.45rem;
  cursor: pointer;
}
</style>

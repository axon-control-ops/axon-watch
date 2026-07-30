<script setup lang="ts">
import type { WorkerDeliveryPipelineView } from '../../lib/worker-delivery-pipeline-view';

defineProps<{
  pipeline: WorkerDeliveryPipelineView;
}>();
</script>

<template>
  <div class="dock-delivery-pipeline" aria-label="Workspace delivery pipeline">
    <p class="dock-delivery-pipeline__title">
      Delivery · {{ pipeline.label }}
    </p>
    <ol class="dock-delivery-pipeline__steps">
      <li
        v-for="step in pipeline.steps"
        :key="step.id"
        class="dock-delivery-pipeline__step"
        :data-state="step.state"
      >
        {{ step.label }}
      </li>
    </ol>
    <p v-if="pipeline.detail" class="dock-delivery-pipeline__detail">
      {{ pipeline.detail }}
    </p>
    <div class="dock-delivery-pipeline__links">
      <a
        v-if="pipeline.draftPrUrl"
        :href="pipeline.draftPrUrl"
        target="_blank"
        rel="noopener noreferrer"
      >Draft PR</a>
      <a
        v-if="pipeline.ciUrl"
        :href="pipeline.ciUrl"
        target="_blank"
        rel="noopener noreferrer"
      >Watch CI</a>
    </div>
  </div>
</template>

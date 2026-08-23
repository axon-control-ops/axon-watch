<script setup lang="ts">
import { computed, onMounted, onUnmounted } from 'vue';

import {
  closeLeadReviewOverlay,
  leadReviewOverlayError,
  leadReviewOverlayLoading,
  leadReviewOverlayOpen,
  leadReviewOverlayPayload,
} from '../../features/lead-review/lead-review-overlay-state';
import { useShellStore } from '../../stores/shell';

const emit = defineEmits<{
  markComplete: [planId: string];
}>();

const shell = useShellStore();

const payload = leadReviewOverlayPayload;
const loading = leadReviewOverlayLoading;
const error = leadReviewOverlayError;
const open = leadReviewOverlayOpen;

const parsed = computed(() => payload.value?.parsed ?? null);

function dismiss(): void {
  closeLeadReviewOverlay();
}

function onKeydown(event: KeyboardEvent): void {
  if (!open.value) {
    return;
  }
  if (event.key === 'Escape') {
    event.preventDefault();
    dismiss();
  }
}

async function openFullThread(): Promise<void> {
  const threadId = payload.value?.threadId?.trim();
  if (!threadId) {
    return;
  }
  await shell.selectIdeThread(threadId, { forceRefresh: true });
  shell.setLayoutMode('ide');
  dismiss();
}

function markComplete(): void {
  const planId = payload.value?.planId;
  if (!planId) {
    return;
  }
  emit('markComplete', planId);
}

onMounted(() => {
  window.addEventListener('keydown', onKeydown);
});

onUnmounted(() => {
  window.removeEventListener('keydown', onKeydown);
});
</script>

<template>
  <div
    v-if="open"
    class="lead-review-overlay"
    role="dialog"
    aria-modal="true"
    aria-label="Lead review"
  >
    <div class="lead-review-overlay__veil" aria-hidden="true" @click="dismiss" />

    <article class="lead-review-overlay__panel">
      <header class="lead-review-overlay__header">
        <div>
          <p class="lead-review-overlay__eyebrow">Lead review</p>
          <h2 class="lead-review-overlay__title">
            {{ payload?.planLabel || 'Lead plan' }}
          </h2>
          <p v-if="payload?.planGoal && payload.planGoal !== payload.planLabel" class="lead-review-overlay__goal">
            {{ payload.planGoal }}
          </p>
        </div>
        <button type="button" class="lead-review-overlay__dismiss" @click="dismiss">
          Done
        </button>
      </header>

      <div v-if="loading" class="lead-review-overlay__state" role="status">
        Loading Lead rollup…
      </div>

      <div v-else-if="error" class="lead-review-overlay__state lead-review-overlay__state--error" role="alert">
        {{ error }}
      </div>

      <div v-else-if="parsed" class="lead-review-overlay__body">
        <p class="lead-review-overlay__headline">{{ parsed.headline }}</p>

        <dl v-if="parsed.goal || parsed.planId || parsed.workspaceId || parsed.runId" class="lead-review-overlay__meta">
          <div v-if="parsed.goal">
            <dt>Goal</dt>
            <dd>{{ parsed.goal }}</dd>
          </div>
          <div v-if="parsed.planId">
            <dt>Plan</dt>
            <dd>{{ parsed.planId }}</dd>
          </div>
          <div v-if="parsed.workspaceId">
            <dt>Workspace</dt>
            <dd>{{ parsed.workspaceId }}</dd>
          </div>
          <div v-if="parsed.runId">
            <dt>Run</dt>
            <dd>{{ parsed.runId }}</dd>
          </div>
        </dl>

        <section v-if="parsed.outcome" class="lead-review-overlay__outcome">
          <p class="lead-review-overlay__section-label">Outcome</p>
          <p>{{ parsed.outcome }}</p>
        </section>

        <section v-if="parsed.findings.length" class="lead-review-overlay__findings">
          <p class="lead-review-overlay__section-label">Specialist findings</p>
          <ul>
            <li v-for="(finding, index) in parsed.findings" :key="`${finding.owner}-${index}`">
              <div class="lead-review-overlay__finding-head">
                <strong>{{ finding.owner }}</strong>
                <span class="lead-review-overlay__finding-status">{{ finding.status }}</span>
              </div>
              <p v-if="finding.outcome" class="lead-review-overlay__finding-outcome">
                {{ finding.outcome }}
              </p>
              <p v-if="finding.excerpt" class="lead-review-overlay__finding-excerpt">
                {{ finding.excerpt }}
              </p>
              <p v-if="finding.runIds.length" class="lead-review-overlay__finding-runs">
                Runs: {{ finding.runIds.join(', ') }}
              </p>
            </li>
          </ul>
        </section>

        <section v-if="parsed.leadNext" class="lead-review-overlay__next">
          <p class="lead-review-overlay__section-label">Lead next</p>
          <p>{{ parsed.leadNext }}</p>
        </section>

        <p v-if="parsed.footer" class="lead-review-overlay__footer">
          {{ parsed.footer }}
        </p>
      </div>

      <footer class="lead-review-overlay__actions">
        <button
          v-if="payload?.planId"
          type="button"
          class="lead-review-overlay__action lead-review-overlay__action--primary"
          :disabled="shell.leadPlansMutating"
          @click="markComplete"
        >
          Mark review complete
        </button>
        <button
          v-if="payload?.threadId"
          type="button"
          class="lead-review-overlay__action"
          @click="void openFullThread()"
        >
          Open full thread in IDE
        </button>
        <button type="button" class="lead-review-overlay__action" @click="dismiss">
          Dismiss
        </button>
      </footer>
    </article>
  </div>
</template>

<style scoped src="./lead-review-overlay.css"></style>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';

import {
  fetchConstitutionConsoleSnapshot,
  type ConstitutionConsoleSnapshot,
} from '../../api/constitution-api';
import {
  buildConstitutionCountCards,
  buildConstitutionListCards,
} from '../../lib/constitution-overview-view';

const loading = ref(false);
const error = ref<string | null>(null);
const snapshot = ref<ConstitutionConsoleSnapshot | null>(null);

const countCards = computed(() => snapshot.value ? buildConstitutionCountCards(snapshot.value) : []);
const listCards = computed(() => snapshot.value ? buildConstitutionListCards(snapshot.value) : []);

async function refreshConstitution(): Promise<void> {
  loading.value = true;
  error.value = null;
  try {
    snapshot.value = await fetchConstitutionConsoleSnapshot();
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : 'constitution overview load failed';
  } finally {
    loading.value = false;
  }
}

onMounted(() => {
  void refreshConstitution();
});
</script>

<template>
  <section class="constitution-overview">
    <div class="settings-section-toolbar">
      <p class="settings-section-toolbar__copy">
        Read-only Constitution status: proof, missions, decisions, capabilities, ADRs, debt, and health.
      </p>
      <button
        type="button"
        class="operator-settings-form__button operator-settings-form__button--ghost"
        :disabled="loading"
        @click="refreshConstitution"
      >
        {{ loading ? 'Refreshing…' : 'Refresh' }}
      </button>
    </div>

    <p
      v-if="error"
      class="settings-feedback-banner settings-feedback-banner--inline settings-feedback-banner--error"
      role="alert"
    >
      {{ error }}
    </p>

    <div class="constitution-overview__counts" aria-label="Constitution registry counts">
      <article v-for="card in countCards" :key="card.id" class="constitution-overview__count-card">
        <span class="constitution-overview__count-value">{{ card.value }}</span>
        <span class="constitution-overview__count-label">{{ card.label }}</span>
      </article>
    </div>

    <div class="constitution-overview__grid">
      <article v-for="card in listCards" :key="card.id" class="constitution-overview__list-card">
        <h3>{{ card.label }}</h3>
        <ul v-if="card.items.length">
          <li v-for="item in card.items" :key="item">{{ item }}</li>
        </ul>
        <p v-else class="constitution-overview__empty">{{ card.empty }}</p>
      </article>
    </div>
  </section>
</template>

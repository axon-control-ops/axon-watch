<script setup lang="ts">
import VaultHudPanel from '../vault/VaultHudPanel.vue';
import { useDataSurface } from '../../composables/useDataSurface';
import { formatDataCell } from '../../lib/data-surface-view';

const {
  snapshot,
  loading,
  error,
  tables,
  totalRows,
  exportBusy,
  exportMessage,
  refresh,
  exportDiagnostic,
} = useDataSurface();
</script>

<template>
  <main class="region region-center-workbench data-surface" aria-label="Operator data">
    <VaultHudPanel tag="div" panel-class="data-surface__shell">
      <header class="data-surface__hero">
        <div class="data-surface__hero-copy">
          <p class="data-surface__eyebrow">Operator foundation</p>
          <div class="data-surface__title-row">
            <h1 class="data-surface__title">Data</h1>
          </div>
          <p class="data-surface__subtitle">
            Read-only view of persisted control-plane and watch tables. Message bodies are
            truncated; secret values are never shown.
          </p>
          <div v-if="snapshot" class="data-surface__stat-row">
            <span class="data-surface__stat">
              Tables <strong>{{ tables.length }}</strong>
            </span>
            <span class="data-surface__stat">
              Persisted rows <strong>{{ totalRows }}</strong>
            </span>
            <span class="data-surface__stat">
              Updated <strong>{{ snapshot.updated_at || '—' }}</strong>
            </span>
          </div>
        </div>
        <div class="data-surface__hero-actions">
          <button
            type="button"
            class="data-surface__button"
            :disabled="exportBusy"
            @click="exportDiagnostic"
          >
            {{ exportBusy ? 'Exporting…' : 'Export JSON' }}
          </button>
          <button type="button" class="data-surface__button" :disabled="loading" @click="refresh">
            {{ loading ? 'Refreshing…' : 'Refresh' }}
          </button>
        </div>
      </header>

      <p v-if="error" class="data-surface__error" role="alert">{{ error }}</p>
      <p v-else-if="loading && !snapshot" class="data-surface__loading">Loading operator data…</p>
      <p v-if="exportMessage" class="data-surface__message data-surface__message--ok">
        {{ exportMessage }}
      </p>

      <div v-if="snapshot" class="data-surface__body">
        <VaultHudPanel
          v-for="table in tables"
          :key="table.id"
          panel-class="data-surface__panel"
        >
          <div class="data-surface__panel-head">
            <h2 class="data-surface__panel-title">{{ table.label }}</h2>
            <p class="data-surface__panel-meta">
              Showing {{ table.count }} of {{ table.total }} row(s)
            </p>
          </div>

          <div v-if="table.rows.length" class="data-surface__table-wrap">
            <table class="data-surface__table">
              <thead>
                <tr>
                  <th v-for="column in table.columns" :key="column">{{ column }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(row, rowIndex) in table.rows" :key="`${table.id}-${rowIndex}`">
                  <td v-for="column in table.columns" :key="column" class="data-surface__mono">
                    {{ formatDataCell(row[column]) }}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <p v-else class="data-surface__empty">No persisted rows yet.</p>
        </VaultHudPanel>
      </div>
    </VaultHudPanel>
  </main>
</template>

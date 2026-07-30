<script setup lang="ts">
import { computed } from 'vue';

import { useShellStore } from '../../stores/shell';

const props = defineProps<{
  planId: string;
  mode: string;
  leadName: string;
  title: string;
  queued: number;
  deferred: number;
  assignments: Array<{ role: string; goal: string }>;
  notes: string[];
}>();

const shell = useShellStore();

const modeLabel = computed(() =>
  props.mode === 'decompose' ? 'Decompose' : props.mode === 'fan_out' ? 'Fan-out' : props.title,
);

const shortPlanId = computed(() => {
  const id = props.planId.trim();
  if (!id) {
    return null;
  }
  return id.length > 22 ? `${id.slice(0, 12)}…${id.slice(-4)}` : id;
});

function openTaskBoard(): void {
  shell.setLayoutMode('operator');
  shell.focusOperatorTaskBoard();
}

async function openSpecialist(role: string): Promise<void> {
  const cleaned = role.trim().toLowerCase();
  const employee = shell.companyEmployeesForCurrentWorkspace.find(
    (row) => String(row.role || '').trim().toLowerCase() === cleaned,
  );
  if (!employee) {
    shell.setLayoutMode('ide');
    return;
  }
  await shell.openOrFocusEmployeeIdeThread(employee);
  shell.setLayoutMode('ide');
}
</script>

<template>
  <article class="lead-fanout" :data-mode="mode">
    <header class="lead-fanout__head">
      <div class="lead-fanout__identity">
        <span class="lead-fanout__mark" aria-hidden="true" />
        <div class="lead-fanout__titles">
          <p class="lead-fanout__kicker">Lead {{ modeLabel }}</p>
          <p class="lead-fanout__lead">{{ leadName }}</p>
        </div>
      </div>
      <code v-if="shortPlanId" class="lead-fanout__plan" :title="planId">{{ shortPlanId }}</code>
    </header>

    <div class="lead-fanout__stats" aria-label="Dispatch status">
      <span class="lead-fanout__stat">
        <strong>{{ queued }}</strong>
        queued
      </span>
      <span class="lead-fanout__stat">
        <strong>{{ deferred }}</strong>
        deferred
      </span>
      <span class="lead-fanout__stat lead-fanout__stat--roles">
        <strong>{{ assignments.length }}</strong>
        roles
      </span>
    </div>

    <ul v-if="assignments.length" class="lead-fanout__roles" aria-label="Specialist assignments">
      <li v-for="row in assignments" :key="`${row.role}-${row.goal.slice(0, 24)}`">
        <button
          type="button"
          class="lead-fanout__role"
          :title="`Open ${row.role}`"
          @click="void openSpecialist(row.role)"
        >
          <span class="lead-fanout__role-name">{{ row.role }}</span>
          <span class="lead-fanout__role-goal">{{ row.goal }}</span>
        </button>
      </li>
    </ul>

    <ul v-if="notes.length" class="lead-fanout__notes">
      <li v-for="(note, index) in notes.slice(0, 3)" :key="`${index}-${note.slice(0, 20)}`">
        {{ note }}
      </li>
    </ul>

    <footer class="lead-fanout__footer">
      <button type="button" class="lead-fanout__action" @click="openTaskBoard">
        Task board
      </button>
      <span class="lead-fanout__hint">Specialist work runs in their threads — not here.</span>
    </footer>
  </article>
</template>

<style scoped>
.lead-fanout {
  display: grid;
  gap: 0.55rem;
  margin: 0.15rem 0 0.35rem;
  padding: 0.7rem 0.75rem 0.65rem;
  border: 1px solid rgba(90, 210, 255, 0.28);
  border-radius: 0.7rem;
  background:
    radial-gradient(ellipse at 8% 0%, rgba(0, 170, 255, 0.16), transparent 45%),
    radial-gradient(ellipse at 90% 100%, rgba(255, 90, 160, 0.08), transparent 40%),
    rgba(2, 12, 20, 0.88);
  box-shadow:
    inset 0 0 0 1px rgba(120, 230, 255, 0.06),
    0 0 1.1rem rgba(0, 140, 200, 0.14);
}

.lead-fanout[data-mode='decompose'] {
  border-color: rgba(110, 220, 255, 0.34);
}

.lead-fanout[data-mode='fan_out'] {
  border-color: rgba(120, 255, 200, 0.3);
}

.lead-fanout__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.55rem;
}

.lead-fanout__identity {
  display: flex;
  align-items: center;
  gap: 0.45rem;
  min-width: 0;
}

.lead-fanout__mark {
  width: 0.55rem;
  height: 0.55rem;
  border-radius: 50%;
  background: rgba(90, 230, 255, 0.95);
  box-shadow: 0 0 0.7rem rgba(0, 220, 255, 0.55);
  flex: 0 0 auto;
  animation: lead-fanout-pulse 2.2s ease-in-out infinite;
}

.lead-fanout__titles {
  min-width: 0;
}

.lead-fanout__kicker {
  margin: 0;
  color: rgba(140, 220, 245, 0.88);
  font: 650 0.55rem/1.1 var(--font-mono, ui-monospace, monospace);
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.lead-fanout__lead {
  margin: 0.12rem 0 0;
  color: rgba(236, 250, 255, 0.98);
  font: 700 0.95rem/1.15 var(--font-display, ui-sans-serif, system-ui);
  letter-spacing: 0.02em;
}

.lead-fanout__plan {
  max-width: 9rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  padding: 0.22rem 0.45rem;
  border: 1px solid rgba(100, 200, 240, 0.3);
  border-radius: 999px;
  background: rgba(0, 24, 36, 0.65);
  color: rgba(170, 230, 255, 0.92);
  font: 0.55rem/1 var(--font-mono, ui-monospace, monospace);
  letter-spacing: 0.04em;
}

.lead-fanout__stats {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
}

.lead-fanout__stat {
  display: inline-flex;
  align-items: baseline;
  gap: 0.28rem;
  padding: 0.22rem 0.5rem;
  border: 1px solid rgba(90, 190, 230, 0.22);
  border-radius: 999px;
  background: rgba(0, 22, 34, 0.55);
  color: rgba(160, 200, 215, 0.88);
  font: 0.58rem/1 var(--font-mono, ui-monospace, monospace);
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.lead-fanout__stat strong {
  color: rgba(230, 250, 255, 0.98);
  font-size: 0.72rem;
  letter-spacing: 0.02em;
}

.lead-fanout__roles {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 0.35rem;
}

.lead-fanout__role {
  display: grid;
  grid-template-columns: 6.2rem minmax(0, 1fr);
  gap: 0.45rem;
  align-items: start;
  width: 100%;
  padding: 0.45rem 0.55rem;
  border: 1px solid rgba(90, 190, 230, 0.2);
  border-radius: 0.45rem;
  background: rgba(3, 16, 26, 0.72);
  color: inherit;
  text-align: left;
  cursor: pointer;
  transition:
    border-color 140ms ease,
    box-shadow 140ms ease,
    transform 140ms ease;
}

.lead-fanout__role:hover {
  transform: translateY(-1px);
  border-color: rgba(120, 230, 255, 0.45);
  box-shadow: 0 0 0.8rem rgba(0, 180, 255, 0.16);
}

.lead-fanout__role-name {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 1.35rem;
  padding: 0.12rem 0.35rem;
  border: 1px solid rgba(110, 220, 255, 0.35);
  border-radius: 999px;
  background: rgba(0, 50, 70, 0.45);
  color: rgba(180, 240, 255, 0.96);
  font: 650 0.54rem/1 var(--font-mono, ui-monospace, monospace);
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

.lead-fanout__role-goal {
  color: rgba(230, 246, 255, 0.96);
  font: 0.74rem/1.35 var(--font-ui, system-ui, sans-serif);
  overflow-wrap: anywhere;
  word-break: break-word;
}

.lead-fanout__notes {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 0.2rem;
}

.lead-fanout__notes li {
  color: rgba(150, 195, 210, 0.88);
  font: 0.62rem/1.35 var(--font-ui, system-ui, sans-serif);
}

.lead-fanout__footer {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.45rem 0.7rem;
  padding-top: 0.15rem;
  border-top: 1px solid rgba(80, 180, 220, 0.14);
}

.lead-fanout__action {
  border: 1px solid rgba(100, 230, 255, 0.4);
  border-radius: 999px;
  background: rgba(0, 50, 70, 0.55);
  color: rgba(210, 245, 255, 0.98);
  font: 650 0.62rem/1 var(--font-mono, ui-monospace, monospace);
  letter-spacing: 0.1em;
  text-transform: uppercase;
  padding: 0.35rem 0.7rem;
  cursor: pointer;
}

.lead-fanout__action:hover {
  border-color: rgba(140, 245, 255, 0.7);
  box-shadow: 0 0 0.7rem rgba(0, 210, 255, 0.25);
}

.lead-fanout__hint {
  color: rgba(140, 185, 205, 0.78);
  font: 0.58rem/1.3 var(--font-ui, system-ui, sans-serif);
}

@keyframes lead-fanout-pulse {
  0%,
  100% {
    opacity: 0.65;
    transform: scale(0.92);
  }
  50% {
    opacity: 1;
    transform: scale(1.08);
  }
}

@media (prefers-reduced-motion: reduce) {
  .lead-fanout__mark,
  .lead-fanout__role:hover {
    animation: none;
    transform: none;
  }
}

@media (max-width: 520px) {
  .lead-fanout__role {
    grid-template-columns: 1fr;
  }
}
</style>

<script setup lang="ts">
import { computed } from 'vue';

import { buildJarvisOpsView } from '../../lib/operator-jarvis-ops-view';
import { useShellStore } from '../../stores/shell';

const shell = useShellStore();

const view = computed(() =>
  buildJarvisOpsView({
    briefing: shell.operatorBriefing,
    primaryActiveRun: shell.primaryActiveRun,
    fleetActiveRuns: shell.runtimeSummary?.active_runs ?? shell.operatorBriefing?.active_runs ?? [],
    ideComposerActivity: shell.ideComposerActivity,
    employees: shell.companyEmployeesFleet,
    agentStreamActive: shell.agentStreamActive,
  }),
);

function onCardActivate(kind: string, id: string): void {
  // #region agent log
  fetch('http://127.0.0.1:7706/ingest/90bcaec2-2b39-4d4a-84b5-157c12735440',{method:'POST',headers:{'Content-Type':'application/json','X-Debug-Session-Id':'fc0b35'},body:JSON.stringify({sessionId:'fc0b35',runId:'jarvis-ops',hypothesisId:'OPS1',location:'OperatorJarvisOpsPanel.vue:onCardActivate',message:'jarvis ops card activated',data:{kind,id,cardCount:view.value.cards.length},timestamp:Date.now()})}).catch(()=>{});
  // #endregion
  if (kind === 'command') {
    shell.focusCommandSeam();
    return;
  }
  if (kind === 'agent') {
    shell.revealTeamRosterForActiveEmployee();
    return;
  }
  shell.focusMissionControl();
}
</script>

<template>
  <div class="jarvis-ops" aria-label="JARVIS operations panel">
    <header class="jarvis-ops__header">
      <p class="jarvis-ops__eyebrow">JARVIS // OPS</p>
      <p class="jarvis-ops__headline">{{ view.headline }}</p>
    </header>
    <p v-if="view.cards.length === 0" class="jarvis-ops__empty">
      No live runs, polls, or agent work right now. Terminal remains available on the TERMINAL tab.
    </p>
    <ul v-else class="jarvis-ops__grid">
      <li
        v-for="card in view.cards"
        :key="card.id"
        class="jarvis-ops__card"
        :data-kind="card.kind"
        :data-tone="card.tone"
      >
        <button
          type="button"
          class="jarvis-ops__card-btn"
          @click="onCardActivate(card.kind, card.id)"
        >
          <span class="jarvis-ops__kind">{{ card.kind }}</span>
          <span class="jarvis-ops__title">{{ card.title }}</span>
          <span class="jarvis-ops__detail">{{ card.detail }}</span>
          <span v-if="card.meta" class="jarvis-ops__meta">{{ card.meta }}</span>
        </button>
      </li>
    </ul>
  </div>
</template>

<style scoped>
.jarvis-ops {
  height: 100%;
  min-height: 0;
  overflow: auto;
  padding: 0.75rem 1rem 1rem;
  background:
    radial-gradient(ellipse at 10% 0%, rgba(0, 140, 200, 0.12), transparent 45%),
    linear-gradient(180deg, rgba(6, 14, 22, 0.96), rgba(4, 10, 16, 0.98));
}

.jarvis-ops__header {
  margin-bottom: 0.75rem;
}

.jarvis-ops__eyebrow {
  margin: 0;
  color: rgba(120, 210, 255, 0.72);
  font-family: var(--font-mono, ui-monospace, SFMono-Regular, Menlo, Consolas, monospace);
  font-size: 0.62rem;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.jarvis-ops__headline {
  margin: 0.2rem 0 0;
  color: rgba(230, 246, 255, 0.94);
  font-family: var(--font-mono, ui-monospace, SFMono-Regular, Menlo, Consolas, monospace);
  font-size: 0.86rem;
  letter-spacing: 0.02em;
}

.jarvis-ops__empty {
  margin: 0;
  color: rgba(160, 190, 210, 0.72);
  font-size: 0.78rem;
  line-height: 1.4;
}

.jarvis-ops__grid {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(14rem, 1fr));
  gap: 0.55rem;
}

.jarvis-ops__card-btn {
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 0.2rem;
  padding: 0.55rem 0.65rem;
  border-radius: 0.55rem;
  border: 1px solid rgba(100, 180, 220, 0.22);
  background: rgba(10, 24, 36, 0.72);
  color: inherit;
  text-align: left;
  cursor: pointer;
}

.jarvis-ops__card-btn:hover {
  border-color: rgba(120, 220, 255, 0.45);
  background: rgba(14, 36, 52, 0.88);
}

.jarvis-ops__card[data-tone='attention'] .jarvis-ops__card-btn {
  border-color: rgba(255, 180, 90, 0.4);
}

.jarvis-ops__card[data-tone='critical'] .jarvis-ops__card-btn {
  border-color: rgba(255, 110, 90, 0.45);
}

.jarvis-ops__kind {
  color: rgba(120, 210, 255, 0.7);
  font-family: var(--font-mono, ui-monospace, SFMono-Regular, Menlo, Consolas, monospace);
  font-size: 0.58rem;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.jarvis-ops__title {
  color: rgba(235, 248, 255, 0.95);
  font-size: 0.8rem;
  font-weight: 600;
  line-height: 1.2;
}

.jarvis-ops__detail {
  color: rgba(170, 210, 230, 0.78);
  font-size: 0.7rem;
  line-height: 1.3;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.jarvis-ops__meta {
  color: rgba(140, 190, 210, 0.65);
  font-family: var(--font-mono, ui-monospace, SFMono-Regular, Menlo, Consolas, monospace);
  font-size: 0.6rem;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}
</style>

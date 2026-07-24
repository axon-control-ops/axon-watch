<script setup lang="ts">
import { computed } from 'vue';

import { buildSidebarAgentTranscriptLines } from '../../lib/sidebar-agent-transcript-view';
import { isActiveRun } from '../../stores/shell-run-selection';
import { useShellStore } from '../../stores/shell';

const shell = useShellStore();

const workspaceId = computed(() => shell.currentWorkspace?.workspace_id ?? null);
const activeRuns = computed(() =>
  shell.runs
    .filter(
      (run) =>
        run.workspace_id === workspaceId.value &&
        isActiveRun(run),
    )
    .slice(0, 5),
);
const activeTasks = computed(() =>
  shell.workspaceTasksForCurrentWorkspace
    .filter((task) => task.status === 'open' || task.status === 'leased')
    .slice(0, 5),
);
const activeSignals = computed(() =>
  shell.inboxItems
    .filter(
      (signal) =>
        signal.workspace_id === workspaceId.value &&
        signal.status !== 'resolved' &&
        signal.status !== 'suppressed',
    )
    .slice(0, 5),
);
const transcriptLines = computed(() =>
  buildSidebarAgentTranscriptLines(shell.latestWorkspaceAgentOutput ?? '', {
    streaming: shell.agentStreamActive,
    maxLines: 24,
  }),
);
const recentReceipts = computed(() =>
  shell.operatorThreadMessages
    .filter((message) => message.role === 'system' || message.role === 'agent')
    .slice(-5)
    .reverse(),
);
const hasOperationalActivity = computed(
  () =>
    activeRuns.value.length > 0 ||
    activeTasks.value.length > 0 ||
    activeSignals.value.length > 0 ||
    transcriptLines.value.length > 0 ||
    recentReceipts.value.length > 0,
);

function shortId(value: string): string {
  const parts = value.split('_');
  return (parts.at(-1) ?? value).slice(0, 8);
}

function compactText(value: string, max = 180): string {
  const text = value.replace(/\s+/g, ' ').trim();
  return text.length > max ? `${text.slice(0, max - 1).trimEnd()}…` : text;
}

function refresh(): void {
  const currentWorkspaceId = workspaceId.value;
  if (!currentWorkspaceId) {
    return;
  }
  void Promise.all([
    shell.loadRuns(),
    shell.loadInbox(),
    shell.loadWorkspaceTasks(currentWorkspaceId),
    shell.refreshOperatorThreadMessages(currentWorkspaceId),
  ]);
}

function openIde(): void {
  shell.setLayoutMode('ide');
}
</script>

<template>
  <section class="mission-control-activity" aria-label="Live workspace operations">
    <header class="mission-control-activity__summary">
      <div>
        <p class="mission-control-activity__eyebrow">Workspace pulse</p>
        <p class="mission-control-activity__workspace">
          {{ workspaceId ?? 'No workspace selected' }}
        </p>
      </div>
      <div class="mission-control-activity__actions">
        <button type="button" @click="refresh">Refresh</button>
        <button type="button" @click="openIde">Open IDE</button>
      </div>
    </header>

    <div class="mission-control-activity__metrics" aria-label="Operational counts">
      <span><strong>{{ activeRuns.length }}</strong> active runs</span>
      <span><strong>{{ activeTasks.length }}</strong> open tasks</span>
      <span><strong>{{ activeSignals.length }}</strong> signals</span>
    </div>

    <div class="mission-control-activity__scroll">
      <section v-if="activeRuns.length" class="mission-control-activity__section">
        <h3>Autonomous workers</h3>
        <article
          v-for="run in activeRuns"
          :key="run.run_id"
          class="mission-control-activity__row mission-control-activity__row--run"
        >
          <div class="mission-control-activity__row-head">
            <span>{{ run.employee_role || run.mode }}</span>
            <span>{{ run.phase }} · #{{ shortId(run.run_id) }}</span>
          </div>
          <p>{{ compactText(run.summary || run.detail || 'Run in progress') }}</p>
          <small v-if="run.current_step">{{ compactText(run.current_step, 120) }}</small>
        </article>
      </section>

      <section v-if="activeTasks.length" class="mission-control-activity__section">
        <h3>Task queue</h3>
        <article
          v-for="task in activeTasks"
          :key="task.task_id"
          class="mission-control-activity__row mission-control-activity__row--task"
        >
          <div class="mission-control-activity__row-head">
            <span>{{ task.owner_role || 'unassigned' }}</span>
            <span>{{ task.status }} · {{ task.attempts_used }}/{{ task.attempt_budget }}</span>
          </div>
          <p>{{ compactText(task.goal) }}</p>
        </article>
      </section>

      <section v-if="transcriptLines.length" class="mission-control-activity__section">
        <h3>{{ shell.agentStreamActive ? 'Live agent stream' : 'Latest agent output' }}</h3>
        <ol class="mission-control-activity__transcript">
          <li
            v-for="line in transcriptLines"
            :key="line.id"
            :data-kind="line.kind"
            :data-live="line.live ? 'true' : 'false'"
          >
            <span>{{ line.kind }}</span>
            <p>{{ line.text }}</p>
          </li>
        </ol>
      </section>

      <section v-if="activeSignals.length" class="mission-control-activity__section">
        <h3>Attention</h3>
        <article
          v-for="signal in activeSignals"
          :key="signal.signal_id"
          class="mission-control-activity__row mission-control-activity__row--signal"
        >
          <div class="mission-control-activity__row-head">
            <span>{{ signal.source }}</span>
            <span>{{ signal.severity }}</span>
          </div>
          <p>{{ compactText(signal.title || signal.summary) }}</p>
        </article>
      </section>

      <section v-if="recentReceipts.length" class="mission-control-activity__section">
        <h3>Recent receipts</h3>
        <article
          v-for="message in recentReceipts"
          :key="message.message_id"
          class="mission-control-activity__row"
        >
          <div class="mission-control-activity__row-head">
            <span>{{ message.role }}</span>
            <span>{{ message.run_id ? `#${shortId(message.run_id)}` : 'workspace' }}</span>
          </div>
          <p>{{ compactText(message.content) }}</p>
        </article>
      </section>

      <div v-if="!hasOperationalActivity" class="mission-control-activity__idle">
        <strong>Workspace is quiet.</strong>
        <p>New worker runs, CI repairs, receipts, and signals will appear here automatically.</p>
      </div>
    </div>
  </section>
</template>

<style scoped>
.mission-control-activity {
  display: flex;
  flex: 1 1 auto;
  flex-direction: column;
  min-height: 0; color: rgba(226, 232, 240, 0.94);
}
.mission-control-activity__summary,
.mission-control-activity__row-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.55rem;
}
.mission-control-activity__summary {
  padding: 0.55rem 0.65rem 0.45rem;
  border-bottom: 1px solid rgba(0, 242, 255, 0.12);
}

.mission-control-activity__eyebrow,
.mission-control-activity__workspace,
.mission-control-activity__row p,
.mission-control-activity__row small,
.mission-control-activity__idle p {
  margin: 0;
}

.mission-control-activity__eyebrow,
.mission-control-activity__section h3,
.mission-control-activity__row-head,
.mission-control-activity__transcript span {
  font-family: var(--font-mono);
  text-transform: uppercase;
}

.mission-control-activity__eyebrow {
  color: rgba(0, 242, 255, 0.74);
  font-size: 0.5rem;
  letter-spacing: 0.1em;
}

.mission-control-activity__workspace {
  margin-top: 0.12rem;
  color: rgba(203, 213, 225, 0.8);
  font-size: 0.58rem;
}

.mission-control-activity__actions { display: flex; gap: 0.3rem; }

.mission-control-activity__actions button {
  padding: 0.2rem 0.42rem;
  border: 1px solid rgba(0, 242, 255, 0.24);
  border-radius: 0.24rem;
  background: rgba(0, 242, 255, 0.05);
  color: rgba(186, 230, 253, 0.92);
  cursor: pointer;
  font: 0.5rem var(--font-mono);
  text-transform: uppercase;
}

.mission-control-activity__metrics {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  border-bottom: 1px solid rgba(0, 242, 255, 0.1);
}

.mission-control-activity__metrics span {
  padding: 0.38rem 0.25rem;
  color: rgba(148, 163, 184, 0.86);
  font: 0.5rem var(--font-mono);
  text-align: center;
  text-transform: uppercase;
}

.mission-control-activity__scroll {
  flex: 1 1 auto;
  min-height: 0;
  padding: 0.5rem;
  overflow: auto;
  overscroll-behavior: contain;
}

.mission-control-activity__section + .mission-control-activity__section { margin-top: 0.65rem; }

.mission-control-activity__section h3 {
  margin: 0 0 0.3rem;
  color: rgba(148, 163, 184, 0.78);
  font-size: 0.5rem;
  letter-spacing: 0.08em;
}

.mission-control-activity__row,
.mission-control-activity__transcript li {
  padding: 0.4rem 0.45rem;
  border-left: 2px solid rgba(100, 116, 139, 0.38);
  background: rgba(6, 14, 22, 0.56);
}

.mission-control-activity__row + .mission-control-activity__row,
.mission-control-activity__transcript li + li { margin-top: 0.25rem; }

.mission-control-activity__row--run { border-left-color: rgba(0, 242, 255, 0.58); }
.mission-control-activity__row--task { border-left-color: rgba(74, 222, 128, 0.52); }
.mission-control-activity__row--signal { border-left-color: rgba(251, 191, 36, 0.62); }

.mission-control-activity__row-head {
  color: rgba(148, 163, 184, 0.85);
  font-size: 0.48rem;
  letter-spacing: 0.05em;
}

.mission-control-activity__row p {
  margin-top: 0.22rem;
  font-size: 0.62rem;
  line-height: 1.38;
}

.mission-control-activity__row small {
  display: block;
  margin-top: 0.2rem;
  color: rgba(148, 163, 184, 0.8);
  font-size: 0.54rem;
}

.mission-control-activity__transcript { margin: 0; padding: 0; list-style: none; }

.mission-control-activity__transcript li {
  display: grid;
  grid-template-columns: 3.6rem minmax(0, 1fr);
  gap: 0.4rem;
}

.mission-control-activity__transcript li[data-live='true'] {
  border-left-color: rgba(0, 242, 255, 0.7); background: rgba(0, 242, 255, 0.07);
}

.mission-control-activity__transcript span {
  color: rgba(148, 163, 184, 0.82); font-size: 0.48rem;
}

.mission-control-activity__transcript p {
  margin: 0;
  font-size: 0.6rem;
  line-height: 1.35;
  white-space: pre-wrap;
  word-break: break-word;
}

.mission-control-activity__idle {
  margin: 1rem 0.2rem;
  padding: 0.75rem;
  border: 1px dashed rgba(0, 242, 255, 0.2);
  color: rgba(148, 163, 184, 0.85);
  font-size: 0.62rem;
  line-height: 1.45;
  text-align: center;
}

.mission-control-activity__idle strong { color: rgba(203, 213, 225, 0.94); }
</style>

<script setup lang="ts">
import type { AgentQuestionOption } from '../../lib/agent-question-view';
import type { LeadCheckinFindingView } from '../../lib/lead-checkin-card';
import AgentQuestionBlock from './AgentQuestionBlock.vue';

defineProps<{
  title: string;
  summary: string;
  findings: LeadCheckinFindingView[];
  nextSteps: string[];
  prompt: string;
  options: AgentQuestionOption[];
  messageId?: string;
  segmentIndex?: number;
  answeredOption?: AgentQuestionOption | null;
}>();
</script>

<template>
  <article class="lead-checkin" data-mode="checkin">
    <header class="lead-checkin__head">
      <div>
        <p class="lead-checkin__kicker">Lead team health</p>
        <h3 class="lead-checkin__title">{{ title }}</h3>
      </div>
      <span class="lead-checkin__summary">{{ summary }}</span>
    </header>

    <ul v-if="findings.length" class="lead-checkin__findings">
      <li
        v-for="finding in findings"
        :key="finding.title + finding.kind"
        class="lead-checkin__finding"
        :class="{
          'lead-checkin__finding--escalate': finding.escalate,
          [`lead-checkin__finding--${finding.decision?.cardType}`]: !!finding.decision,
        }"
      >
        <span class="lead-checkin__kind">{{ finding.kindLabel }}</span>
        <span v-if="finding.decision" class="lead-checkin__card-type">{{
          finding.decision.cardType.replace('_', ' ')
        }}</span>
        <p class="lead-checkin__finding-title">{{ finding.title }}</p>
        <p class="lead-checkin__finding-detail">{{ finding.detail }}</p>
        <p v-if="finding.decision?.recommendedAction" class="lead-checkin__finding-action">
          {{ finding.decision.recommendedAction }}
        </p>
      </li>
    </ul>
    <p v-else class="lead-checkin__clear">No failed shifts or degraded signals this pass.</p>

    <section class="lead-checkin__next" aria-label="Next steps">
      <p class="lead-checkin__next-label">Next steps</p>
      <ol>
        <li v-for="step in nextSteps" :key="step">{{ step }}</li>
      </ol>
    </section>

    <AgentQuestionBlock
      v-if="options.length"
      :prompt="prompt"
      :options="options"
      :message-id="messageId"
      :segment-index="segmentIndex"
      :answered-option="answeredOption"
    />
  </article>
</template>

<style scoped>
.lead-checkin {
  display: grid;
  gap: 0.65rem;
  margin: 0.15rem 0 0.4rem;
  padding: 0.75rem 0.8rem 0.7rem;
  border: 1px solid rgba(255, 180, 90, 0.28);
  border-radius: 0.7rem;
  background:
    radial-gradient(ellipse at 8% 0%, rgba(255, 160, 60, 0.12), transparent 48%),
    rgba(12, 10, 8, 0.92);
}

.lead-checkin__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.6rem;
}

.lead-checkin__kicker {
  margin: 0;
  color: rgba(255, 200, 130, 0.9);
  font: 650 0.55rem/1.1 var(--font-mono, ui-monospace, monospace);
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.lead-checkin__title {
  margin: 0.15rem 0 0;
  color: rgba(255, 246, 236, 0.98);
  font: 700 0.92rem/1.2 var(--font-display, ui-sans-serif, system-ui);
}

.lead-checkin__summary {
  flex: 0 0 auto;
  padding: 0.22rem 0.5rem;
  border: 1px solid rgba(255, 180, 90, 0.32);
  border-radius: 999px;
  color: rgba(255, 220, 170, 0.95);
  font: 650 0.58rem/1 var(--font-mono, ui-monospace, monospace);
}

.lead-checkin__findings {
  margin: 0;
  padding: 0;
  list-style: none;
  display: grid;
  gap: 0.45rem;
}

.lead-checkin__finding {
  padding: 0.5rem 0.55rem;
  border: 1px solid rgba(255, 120, 100, 0.28);
  border-radius: 0.45rem;
  background: rgba(50, 16, 12, 0.35);
}

.lead-checkin__finding--escalate {
  border-color: rgba(255, 190, 80, 0.4);
  background: rgba(50, 32, 8, 0.4);
}

.lead-checkin__finding--working,
.lead-checkin__finding--recovered {
  border-color: rgba(120, 200, 255, 0.32);
  background: rgba(10, 24, 36, 0.4);
}

.lead-checkin__finding--completed {
  border-color: rgba(120, 220, 150, 0.32);
  background: rgba(10, 32, 18, 0.4);
}

.lead-checkin__finding--blocked,
.lead-checkin__finding--failed {
  border-color: rgba(255, 190, 80, 0.4);
  background: rgba(50, 32, 8, 0.4);
}

.lead-checkin__kind {
  display: inline-block;
  margin-bottom: 0.2rem;
  color: rgba(255, 180, 150, 0.92);
  font: 650 0.52rem/1 var(--font-mono, ui-monospace, monospace);
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

.lead-checkin__card-type {
  display: inline-block;
  margin: 0 0 0.2rem 0.4rem;
  padding: 0.05rem 0.4rem;
  border: 1px solid rgba(255, 255, 255, 0.18);
  border-radius: 999px;
  color: rgba(230, 230, 230, 0.85);
  font: 650 0.5rem/1.2 var(--font-mono, ui-monospace, monospace);
  letter-spacing: 0.08em;
  text-transform: capitalize;
}

.lead-checkin__finding-title,
.lead-checkin__finding-detail,
.lead-checkin__finding-action,
.lead-checkin__clear {
  margin: 0;
  color: rgba(240, 236, 230, 0.96);
  font: 600 0.78rem/1.35 var(--font-ui, ui-sans-serif, system-ui);
}

.lead-checkin__finding-detail,
.lead-checkin__clear {
  margin-top: 0.2rem;
  color: rgba(210, 200, 190, 0.9);
  font-weight: 500;
  font-size: 0.72rem;
}

.lead-checkin__finding-action {
  margin-top: 0.3rem;
  color: rgba(180, 220, 255, 0.92);
  font-weight: 600;
  font-size: 0.72rem;
}

.lead-checkin__next {
  padding: 0.5rem 0.55rem;
  border: 1px solid rgba(120, 200, 255, 0.2);
  border-radius: 0.45rem;
  background: rgba(8, 18, 28, 0.55);
}

.lead-checkin__next-label {
  margin: 0 0 0.3rem;
  color: rgba(150, 220, 255, 0.92);
  font: 650 0.55rem/1.1 var(--font-mono, ui-monospace, monospace);
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.lead-checkin__next ol {
  margin: 0;
  padding-left: 1.1rem;
  color: rgba(220, 230, 240, 0.94);
  font: 500 0.72rem/1.45 var(--font-ui, ui-sans-serif, system-ui);
}

.lead-checkin__next li + li {
  margin-top: 0.2rem;
}
</style>

<script setup lang="ts">
import { computed, onMounted, onUnmounted } from 'vue';

import { OPERATOR_PERSONA_NAME } from '../../lib/operator-persona-name';
import { useShellStore } from '../../stores/shell';
import { buildReportTheaterAttendees } from './report-theater-attendees';
import { executeReportTheaterAction } from './report-theater-execute';
import { polishTheaterLine } from './report-theater-narration';
import {
  closeReportTheater,
  reportTheaterDirectives,
  reportTheaterExecuting,
  reportTheaterFingerprint,
  reportTheaterOpen,
  reportTheaterShowNextSteps,
  reportTheaterSpeakerName,
  reportTheaterStageIndex,
  reportTheaterStages,
  reportTheaterAttendeesRoster,
} from './report-theater-state';

const shell = useShellStore();

const stages = reportTheaterStages;
const activeIndex = reportTheaterStageIndex;
const showNextSteps = reportTheaterShowNextSteps;
const executing = reportTheaterExecuting;

const readiness = computed(() => shell.operatorBriefing?.production_readiness ?? null);
const readinessBlocker = computed(() => {
  const blocker = readiness.value?.blockers?.[0] ?? null;
  if (!blocker) {
    return null;
  }
  return polishTheaterLine(blocker, 72);
});
const activeStage = computed(() => stages.value[activeIndex.value] ?? null);
// Frozen when the theater opens so the displayed promise and executed action
// cannot diverge if live readiness changes while narration is in progress.
const directives = reportTheaterDirectives;
const primaryDirective = computed(() => directives.value.find((item) => item.kind === 'primary') ?? null);
const secondaryDirectives = computed(() =>
  directives.value.filter((item) => item.kind !== 'primary').slice(0, 2),
);

const attendees = computed(() =>
  buildReportTheaterAttendees({
    employees:
      reportTheaterAttendeesRoster.value.length > 0
        ? reportTheaterAttendeesRoster.value
        : (shell.companyEmployeesForCurrentWorkspace ?? []),
    activeLines: [
      ...(activeStage.value?.lines ?? []),
      primaryDirective.value?.label ?? '',
    ],
    stageId: activeStage.value?.id ?? null,
    activeSpeakerName: reportTheaterSpeakerName.value,
    max: 6,
  }),
);

const pulseLabel = computed(() => {
  if (executing.value) {
    return 'Executing';
  }
  if (showNextSteps.value) {
    return 'Directive';
  }
  return activeStage.value?.title ?? 'Opening';
});

const heroMode = computed(() => {
  if (executing.value) {
    return 'executing';
  }
  if (showNextSteps.value) {
    return 'directive';
  }
  if (activeStage.value) {
    return 'stage';
  }
  return 'intro';
});

const boardTitle = computed(() => {
  if (heroMode.value === 'intro') {
    return 'Team stand-up';
  }
  if (heroMode.value === 'executing') {
    return 'Taking initiative';
  }
  if (heroMode.value === 'directive') {
    return 'Next directive';
  }
  return activeStage.value?.title ?? 'Stand-up';
});

type BoardCard = { tag: string | null; body: string };

const boardCards = computed((): BoardCard[] => {
  const stage = activeStage.value;
  if (!stage || heroMode.value !== 'stage') {
    return [];
  }
  const speaker = String(reportTheaterSpeakerName.value || '').trim().toLowerCase();
  let lines = stage.lines.filter((line) => line.trim());
  if (stage.id === 'lead_rollups') {
    if (speaker && speaker !== 'vaxon') {
      const match = lines.find((line) => line.toLowerCase().startsWith(speaker));
      lines = match ? [match] : lines.slice(0, 1);
    } else {
      lines = lines.slice(0, 1);
    }
  } else {
    lines = lines.slice(0, 2);
  }
  return lines.map((line) => {
    if (stage.id === 'lead_rollups' && line.includes(':')) {
      const tag = line.split(':')[0]?.trim() || null;
      const body = polishTheaterLine(line.slice(line.indexOf(':') + 1).trim(), 800);
      return { tag, body };
    }
    return { tag: null, body: polishTheaterLine(line, 800) };
  });
});

function onKeydown(event: KeyboardEvent): void {
  if (!reportTheaterOpen.value) {
    return;
  }
  if (event.key === 'Escape') {
    event.preventDefault();
    shell.interruptKairoVoice();
    closeReportTheater();
  }
}

async function runDirective(directiveId: string): Promise<void> {
  const directive = directives.value.find((item) => item.id === directiveId);
  if (!directive) {
    return;
  }
  if (!directive.briefingAction) {
    closeReportTheater();
    return;
  }
  await executeReportTheaterAction(shell, shell.operatorBriefing, directive.briefingAction);
  closeReportTheater();
}

function dismiss(): void {
  shell.interruptKairoVoice();
  closeReportTheater();
}

onMounted(() => {
  window.addEventListener('keydown', onKeydown);
});

onUnmounted(() => {
  window.removeEventListener('keydown', onKeydown);
});
</script>

<template>
  <Teleport to="body">
    <div
      v-if="reportTheaterOpen"
      class="report-theater"
      role="dialog"
      aria-modal="true"
      aria-label="VAXON team stand-up"
    >
      <div class="report-theater__veil" @click="dismiss" />

      <div class="report-theater__frame" :data-mode="heroMode">
        <div class="report-theater__scan" aria-hidden="true" />
        <div class="report-theater__glow" aria-hidden="true" />

        <header class="report-theater__header">
          <div>
            <p class="report-theater__eyebrow">{{ OPERATOR_PERSONA_NAME }} command theater</p>
            <h2 class="report-theater__title">Stand-up</h2>
          </div>
          <div class="report-theater__meta">
            <span class="report-theater__pulse">{{ pulseLabel }}</span>
            <span
              v-if="readiness"
              class="report-theater__readiness"
              :title="readinessBlocker || undefined"
            >
              {{ readiness.score }}%
            </span>
            <button type="button" class="report-theater__dismiss" @click="dismiss">
              Esc
            </button>
          </div>
        </header>

        <div class="report-theater__gallery" aria-label="Team present">
          <div
            v-for="person in attendees"
            :key="person.id"
            class="report-theater__seat"
            :class="{
              'report-theater__seat--chair': person.kind === 'vaxon',
              'report-theater__seat--lead': person.lead && person.kind !== 'vaxon',
              'report-theater__seat--speaking': person.speaking,
            }"
          >
            <div
              class="report-theater__face"
              :style="{ background: person.avatar.background, color: person.avatar.foreground }"
            >
              <img
                v-if="person.avatar.faceUrl"
                class="report-theater__face-img"
                :src="person.avatar.faceUrl"
                :alt="person.name"
              />
              <span v-else>{{ person.avatar.initials }}</span>
            </div>
            <div class="report-theater__seat-copy">
              <span class="report-theater__seat-name">{{ person.name }}</span>
              <span class="report-theater__seat-status">{{ person.statusLine }}</span>
            </div>
          </div>
        </div>

        <div class="report-theater__stage-rail" aria-hidden="true">
          <span
            v-for="(stage, index) in stages"
            :key="stage.id"
            class="report-theater__rail-dot"
            :class="{
              'report-theater__rail-dot--active': index === activeIndex && heroMode === 'stage',
              'report-theater__rail-dot--done':
                index < activeIndex || heroMode === 'directive' || heroMode === 'executing',
            }"
          />
        </div>

        <div class="report-theater__board" :data-mode="heroMode">
          <p class="report-theater__hero-kicker">{{ boardTitle }}</p>

          <template v-if="heroMode === 'stage' && boardCards.length">
            <ul class="report-theater__hero-lines">
              <li
                v-for="(card, lineIndex) in boardCards"
                :key="`${activeStage?.id}:${card.tag}:${card.body}`"
                class="report-theater__hero-line"
                :class="{ 'report-theater__hero-line--lead': Boolean(card.tag) }"
                :style="{ animationDelay: `${lineIndex * 70}ms` }"
              >
                <template v-if="card.tag">
                  <span class="report-theater__lead-tag">{{ card.tag }}</span>
                  <span>{{ card.body }}</span>
                </template>
                <template v-else>{{ card.body }}</template>
              </li>
            </ul>
          </template>

          <template v-else-if="heroMode === 'intro'">
            <p class="report-theater__hero-directive report-theater__hero-directive--intro">
              Leads are present — compiling the board…
            </p>
          </template>

          <template v-else-if="heroMode === 'executing'">
            <p class="report-theater__hero-directive">
              {{ primaryDirective?.label || 'Switching focus…' }}
            </p>
          </template>

          <template v-else>
            <p class="report-theater__hero-directive">
              {{ primaryDirective?.label || "I'll keep watching the fleet." }}
            </p>
            <p v-if="primaryDirective?.autoExecute" class="report-theater__auto">
              Taking initiative…
            </p>
            <div class="report-theater__actions">
              <button
                v-if="primaryDirective && !primaryDirective.autoExecute"
                type="button"
                class="report-theater__action report-theater__action--primary"
                @click="runDirective(primaryDirective.id)"
              >
                <span class="report-theater__action-label">{{ primaryDirective.label }}</span>
                <span class="report-theater__action-detail">{{ primaryDirective.detail }}</span>
              </button>
              <button
                v-for="directive in secondaryDirectives"
                :key="directive.id"
                type="button"
                class="report-theater__action"
                :class="{ 'report-theater__action--ghost': directive.id === 'vaxon-watch' }"
                @click="runDirective(directive.id)"
              >
                <span class="report-theater__action-label">{{ directive.label }}</span>
              </button>
            </div>
            <p v-if="reportTheaterFingerprint" class="report-theater__fingerprint">
              receipt {{ reportTheaterFingerprint }}
            </p>
          </template>
        </div>

        <p class="report-theater__hint">
          <template v-if="heroMode === 'executing'">{{ OPERATOR_PERSONA_NAME }} is moving</template>
          <template v-else-if="showNextSteps">Esc aborts · otherwise continues</template>
          <template v-else>Voice-synced briefing · Esc to dismiss</template>
        </p>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.report-theater__seat--speaking {
  animation: report-theater-speaker-glow 1.1s ease-in-out infinite alternate;
}

.report-theater__seat--speaking .report-theater__face {
  box-shadow: 0 0 10px currentColor, 0 0 28px rgba(0, 242, 255, 0.9);
}

@keyframes report-theater-speaker-glow {
  from { filter: brightness(1.05); }
  to { filter: brightness(1.5) saturate(1.35); }
}
</style>

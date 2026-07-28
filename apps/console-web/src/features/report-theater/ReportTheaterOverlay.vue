<script setup lang="ts">
import { computed, onMounted, onUnmounted } from 'vue';

import { OPERATOR_PERSONA_NAME } from '../../lib/operator-persona-name';
import { useShellStore } from '../../stores/shell';
import { buildReportTheaterAttendees } from './report-theater-attendees';
import { buildVaxonReportDirectives } from './report-theater-directives';
import { executeReportTheaterAction } from './report-theater-execute';
import { pickReportTheaterActions } from './report-theater-model';
import {
  closeReportTheater,
  reportTheaterExecuting,
  reportTheaterFingerprint,
  reportTheaterOpen,
  reportTheaterShowNextSteps,
  reportTheaterStageIndex,
  reportTheaterStages,
} from './report-theater-state';

const shell = useShellStore();

const stages = reportTheaterStages;
const activeIndex = reportTheaterStageIndex;
const showNextSteps = reportTheaterShowNextSteps;
const executing = reportTheaterExecuting;

const readiness = computed(() => shell.operatorBriefing?.production_readiness ?? null);
const activeStage = computed(() => stages.value[activeIndex.value] ?? null);
const directives = computed(() =>
  buildVaxonReportDirectives({
    nextMove: stages.value[stages.value.length - 1]?.lines[0] ?? '',
    actions: pickReportTheaterActions(shell.operatorBriefing?.next_safe_actions, 3),
    topSignals: shell.operatorBriefing?.top_signals ?? [],
  }),
);
const primaryDirective = computed(() => directives.value.find((item) => item.kind === 'primary') ?? null);
const secondaryDirectives = computed(() =>
  directives.value.filter((item) => item.kind !== 'primary'),
);

const attendees = computed(() =>
  buildReportTheaterAttendees({
    employees: shell.companyEmployeesForCurrentWorkspace ?? [],
    activeLines: [
      ...(activeStage.value?.lines ?? []),
      primaryDirective.value?.label ?? '',
    ],
    stageId: activeStage.value?.id ?? null,
    max: 7,
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
    return 'VAXON directive';
  }
  return activeStage.value?.title ?? 'Stand-up';
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
  // #region agent log
  fetch('http://127.0.0.1:7706/ingest/90bcaec2-2b39-4d4a-84b5-157c12735440',{method:'POST',headers:{'Content-Type':'application/json','X-Debug-Session-Id':'bef50e'},body:JSON.stringify({sessionId:'bef50e',runId:'post-fix',hypothesisId:'H23',location:'ReportTheaterOverlay.vue:runDirective',message:'directive clicked',data:{directiveId,label:directive.label,kind:directive.kind,actionKind:directive.briefingAction?.kind??null,actionTitle:directive.briefingAction?.title??null,signalId:directive.briefingAction?.signal_id??null,autoExecute:directive.autoExecute,layoutMode:shell.layoutMode,centerView:shell.operatorCenterView??null},timestamp:Date.now()})}).catch(()=>{});
  // #endregion
  if (!directive.briefingAction) {
    closeReportTheater();
    return;
  }
  const result = await executeReportTheaterAction(
    shell,
    shell.operatorBriefing,
    directive.briefingAction,
  );
  // #region agent log
  fetch('http://127.0.0.1:7706/ingest/90bcaec2-2b39-4d4a-84b5-157c12735440',{method:'POST',headers:{'Content-Type':'application/json','X-Debug-Session-Id':'bef50e'},body:JSON.stringify({sessionId:'bef50e',runId:'post-fix',hypothesisId:'H23',location:'ReportTheaterOverlay.vue:runDirective:result',message:'directive action executed',data:{directiveId,ok:result.ok,resultKind:'kind' in result ? result.kind : null,reason:'reason' in result ? result.reason : null,layoutModeAfter:shell.layoutMode,centerViewAfter:shell.operatorCenterView??null,leftSidebar:shell.leftSidebarMode??null},timestamp:Date.now()})}).catch(()=>{});
  // #endregion
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
            <p class="report-theater__eyebrow">{{ OPERATOR_PERSONA_NAME }} · team stand-up</p>
            <h2 class="report-theater__title">Stand-up</h2>
          </div>
          <div class="report-theater__meta">
            <span class="report-theater__pulse">{{ pulseLabel }}</span>
            <span v-if="readiness" class="report-theater__readiness">
              Production is {{ readiness.score }}%
            </span>
            <button type="button" class="report-theater__dismiss" @click="dismiss">
              Dismiss
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
              <span class="report-theater__seat-role">
                {{ person.kind === 'vaxon' ? 'Chair' : person.roleLabel }}
              </span>
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

          <template v-if="heroMode === 'stage' && activeStage">
            <ul class="report-theater__hero-lines">
              <li
                v-for="(line, lineIndex) in activeStage.lines.slice(0, 3)"
                :key="`${activeStage.id}:${line}`"
                class="report-theater__hero-line"
                :class="{
                  'report-theater__hero-line--lead': activeStage.id === 'lead_rollups',
                }"
                :style="{ animationDelay: `${lineIndex * 70}ms` }"
              >
                <template v-if="activeStage.id === 'lead_rollups' && line.includes(':')">
                  <span class="report-theater__lead-tag">{{ line.split(':')[0] }}</span>
                  <span>{{ line.slice(line.indexOf(':') + 1).trim() }}</span>
                </template>
                <template v-else>{{ line }}</template>
              </li>
            </ul>
          </template>

          <template v-else-if="heroMode === 'intro'">
            <p class="report-theater__hero-directive report-theater__hero-directive--intro">
              Leads are present — {{ OPERATOR_PERSONA_NAME }} is compiling the board…
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
                <span class="report-theater__action-detail">{{ directive.detail }}</span>
              </button>
            </div>
            <p v-if="reportTheaterFingerprint" class="report-theater__fingerprint">
              receipt {{ reportTheaterFingerprint }}
            </p>
          </template>
        </div>

        <p class="report-theater__hint">
          <template v-if="heroMode === 'executing'">{{ OPERATOR_PERSONA_NAME }} is moving</template>
          <template v-else-if="showNextSteps">Esc aborts · otherwise VAXON continues</template>
          <template v-else>Team briefing synced to {{ OPERATOR_PERSONA_NAME }} · Esc to dismiss</template>
        </p>
      </div>
    </div>
  </Teleport>
</template>

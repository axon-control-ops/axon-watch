<script setup lang="ts">
import { computed } from 'vue';

import type { OperatorBriefing } from '../contracts/canonical';
import type { BriefingVoiceTranscriptEntry } from '../lib/briefing-voice-transcript';
import {
  briefingAdvise,
  briefingConnectivityLabels,
  briefingHasActions,
  briefingHasTopSignals,
  briefingIsEmpty,
  briefingNotice,
  briefingPanelHeadline,
  briefingRhythmField,
  type BriefingPanelLoadState,
} from '../lib/briefing-panel-view';
import { OPERATOR_PERSONA_NAME } from '../lib/operator-persona-name';
import { buildPersonaVoiceLineFallback } from '../lib/persona-voice-line';
import {
  localRuntimeDegradedActive,
  remoteIngressAttentionActive,
} from '../lib/runtime-degraded-scope';
import { useShellStore } from '../stores/shell';
import BriefingOpenLoopsStrip from './BriefingOpenLoopsStrip.vue';

const props = defineProps<{
  briefing: OperatorBriefing | null;
  loadState: BriefingPanelLoadState;
  error: string | null;
  hero?: boolean;
  galaxyCompact?: boolean;
  summaryLine?: string;
  spokenTranscript?: BriefingVoiceTranscriptEntry[];
}>();

const emit = defineEmits<{
  openChat: [];
}>();

const shell = useShellStore();

const headline = computed(() => briefingPanelHeadline(props.briefing, props.loadState));
const heroNotice = computed(() =>
  briefingNotice(props.briefing, props.loadState, {
    primaryActiveRun: shell.primaryActiveRun,
  }),
);
const heroAdvise = computed(() => briefingAdvise(props.briefing, props.loadState));
const heroDecide = computed(() => briefingRhythmField(props.briefing, 'decide', props.loadState));
const heroExecute = computed(() => briefingRhythmField(props.briefing, 'execute', props.loadState));
const heroVerify = computed(() => briefingRhythmField(props.briefing, 'verify', props.loadState));
const heroReport = computed(() => briefingRhythmField(props.briefing, 'report', props.loadState));
const showEmptyState = computed(
  () => props.loadState === 'loaded' && briefingIsEmpty(props.briefing),
);
const showActions = computed(
  () => props.loadState === 'loaded' && briefingHasActions(props.briefing),
);
const showTopSignals = computed(
  () => props.loadState === 'loaded' && briefingHasTopSignals(props.briefing),
);
const connectivityLabels = computed(() =>
  props.briefing ? briefingConnectivityLabels(props.briefing.connectivity) : [],
);
const personaEnabled = computed(
  () => props.briefing?.operator_presence?.settings?.operator_persona_enabled !== false,
);
const personaTitle = computed(() => (personaEnabled.value ? OPERATOR_PERSONA_NAME : 'Operator'));

const voiceLine = computed(() => {
  if (props.briefing?.operator_presence?.persona_voice_line) {
    return props.briefing.operator_presence.persona_voice_line;
  }
  const topSignal = props.briefing?.top_signals?.[0];
  return buildPersonaVoiceLineFallback({
    pendingApprovals: props.briefing?.pending_approvals.count ?? 0,
    topSignalTitle: topSignal?.title,
    topSignalWorkspaceId: topSignal?.workspace_id,
    topSignalSummary: topSignal?.summary,
    degradedActive: localRuntimeDegradedActive(props.briefing?.degraded),
    loadState: props.loadState,
    personaEnabled: personaEnabled.value,
  });
});

const showDegradedBanner = computed(() => Boolean(props.briefing?.degraded.active));
const degradedBannerLabel = computed(() => {
  const reasons = props.briefing?.degraded.reasons?.join(', ') ?? '';
  if (remoteIngressAttentionActive(props.briefing?.degraded)) {
    return `Remote ingress · ${reasons}`;
  }
  return `Degraded state · ${reasons}`;
});

const spokenTranscript = computed(() => props.spokenTranscript ?? []);

function transcriptTimeLabel(value: string): string {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return '';
  }
  return parsed.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}
</script>

<template>
  <div
    class="briefing-panel briefing-panel--mockup"
    :class="{
      'briefing-panel--hero': hero,
      'briefing-panel--galaxy-compact': hero && galaxyCompact,
    }"
  >
    <template v-if="hero && galaxyCompact">
      <p v-if="summaryLine" class="briefing-panel__summary-line">{{ summaryLine }}</p>
      <p class="briefing-panel__galaxy-compact-copy">{{ heroAdvise || heroNotice }}</p>
      <BriefingOpenLoopsStrip :briefing="briefing" compact />
      <p v-if="showDegradedBanner" class="region-copy region-copy--degraded">
        {{ degradedBannerLabel }}
      </p>
      <button type="button" class="briefing-panel__galaxy-compact-link" @click="emit('openChat')">
        Full briefing →
      </button>
    </template>

    <template v-else-if="hero">
      <p v-if="summaryLine" class="briefing-panel__summary-line">{{ summaryLine }}</p>

      <div class="briefing-panel__hero-body">
        <div class="briefing-panel__reactor" aria-hidden="true">
          <span class="briefing-panel__reactor-grid" />
          <span class="briefing-panel__reactor-ring briefing-panel__reactor-ring--outer" />
          <span class="briefing-panel__reactor-ring briefing-panel__reactor-ring--mid" />
          <span class="briefing-panel__reactor-ring briefing-panel__reactor-ring--inner" />
          <span class="briefing-panel__reactor-core" />
          <span class="briefing-panel__reactor-sweep" />
        </div>

        <div class="briefing-panel__voice-copy">
          <p class="briefing-panel__kairo-title">{{ personaTitle }}</p>
          <p class="briefing-panel__section-label briefing-panel__section-label--hero">Notice</p>
          <p class="briefing-panel__kairo-subtitle">{{ heroNotice }}</p>
          <p class="briefing-panel__section-label briefing-panel__section-label--hero">Advise</p>
          <p class="briefing-panel__kairo-advise">{{ heroAdvise }}</p>
          <BriefingOpenLoopsStrip :briefing="briefing" />
          <p v-if="showDegradedBanner" class="region-copy region-copy--degraded">
            {{ degradedBannerLabel }}
          </p>
        </div>
      </div>
    </template>

    <template v-else>
      <div class="briefing-panel__presence briefing-panel__presence--text-only">
        <div class="briefing-panel__voice-copy">
          <p class="briefing-panel__voice-line">{{ voiceLine }}</p>
          <strong class="briefing-panel__headline">{{ headline }}</strong>
        </div>
      </div>

      <p v-if="loadState === 'loading'" class="region-copy">Loading operator briefing…</p>
      <p v-else-if="loadState === 'error'" class="region-copy region-copy--degraded">
        {{ error }}
      </p>

      <template v-else-if="briefing">
        <div class="briefing-panel__section">
          <p class="briefing-panel__section-label">Notice</p>
          <p class="briefing-panel__rhythm-copy">{{ heroNotice }}</p>
        </div>

        <div class="briefing-panel__section">
          <p class="briefing-panel__section-label">Advise</p>
          <p class="briefing-panel__rhythm-copy">{{ heroAdvise }}</p>
        </div>

        <div class="briefing-panel__section">
          <p class="briefing-panel__section-label">Decide</p>
          <p class="briefing-panel__rhythm-copy">{{ heroDecide }}</p>
        </div>

        <div class="briefing-panel__section">
          <p class="briefing-panel__section-label">Execute</p>
          <p class="briefing-panel__rhythm-copy">{{ heroExecute }}</p>
        </div>

        <div class="briefing-panel__section">
          <p class="briefing-panel__section-label">Verify</p>
          <p class="briefing-panel__rhythm-copy">{{ heroVerify }}</p>
        </div>

        <div class="briefing-panel__section">
          <p class="briefing-panel__section-label">Report</p>
          <p class="briefing-panel__rhythm-copy">{{ heroReport }}</p>
        </div>

        <div class="briefing-panel__section">
          <p class="briefing-panel__section-label">Connectivity</p>
          <div class="briefing-panel__chips">
            <span
              v-for="label in connectivityLabels"
              :key="label"
              class="briefing-panel__chip"
              :class="{
                'briefing-panel__chip--ok': label.endsWith('ready') || label.endsWith('connected'),
                'briefing-panel__chip--warn':
                  label.includes('not ready') || label.includes('disconnected'),
              }"
            >
              {{ label }}
            </span>
          </div>
        </div>
      </template>

      <p v-if="showEmptyState" class="region-copy">
        Systems nominal. No pending approvals, top signals, or recommended actions right now.
      </p>

      <div v-if="showTopSignals" class="briefing-panel__section">
        <p class="briefing-panel__section-label">Top signals</p>
        <ul class="briefing-panel__list">
          <li
            v-for="signal in briefing?.top_signals"
            :key="signal.signal_id"
            class="briefing-panel__item"
          >
            <span class="briefing-panel__item-title">{{ signal.title }}</span>
            <span class="region-copy">
              {{ signal.severity }} · {{ signal.status }} · workspace {{ signal.workspace_id }}
            </span>
          </li>
        </ul>
      </div>

      <div v-if="briefing && briefing.pending_approvals.count > 0" class="briefing-panel__section">
        <p class="briefing-panel__section-label">
          Jobs waiting for your yes or no · act in Approvals / Mission Control
        </p>
        <ul class="briefing-panel__list">
          <li
            v-for="(item, index) in briefing.pending_approvals.items"
            :key="item.approval_id"
            class="briefing-panel__item"
          >
            <span class="briefing-panel__item-title">
              Job waiting for your yes or no{{ index === 0 ? ' (primary)' : '' }}
            </span>
            <span class="region-copy">
              run {{ item.run_id }} · workspace {{ item.workspace_id }}
            </span>
            <span class="region-copy briefing-panel__tech-note">ID {{ item.approval_id }}</span>
          </li>
        </ul>
      </div>

      <div v-if="showActions" class="briefing-panel__section">
        <p class="briefing-panel__section-label">Suggested actions · guidance only</p>
        <p class="region-copy">
          Open Mission Control to approve, reject, or resume a run.
        </p>
        <ul class="briefing-panel__list">
          <li
            v-for="action in briefing?.next_safe_actions"
            :key="action.action_id"
            class="briefing-panel__item"
          >
            <span class="briefing-panel__item-title">{{ action.title }}</span>
            <span class="region-copy">{{ action.detail }}</span>
            <span class="briefing-panel__kind">{{ action.kind }}</span>
          </li>
        </ul>
      </div>

      <div v-if="briefing?.memory_highlights?.length" class="briefing-panel__section">
        <p class="briefing-panel__section-label">Operator context</p>
        <ul class="briefing-panel__list">
          <li
            v-for="memory in briefing.memory_highlights"
            :key="memory.memory_id"
            class="briefing-panel__item"
          >
            <span class="briefing-panel__item-title">{{ memory.title }}</span>
            <span class="region-copy">{{ memory.content }}</span>
            <span class="briefing-panel__kind">non-authoritative memory</span>
          </li>
        </ul>
      </div>

      <div v-if="spokenTranscript.length" class="briefing-panel__section">
        <p class="briefing-panel__section-label">Spoken transcript</p>
        <ul class="briefing-panel__list">
          <li
            v-for="entry in spokenTranscript"
            :key="entry.id"
            class="briefing-panel__item"
          >
            <span class="briefing-panel__item-title">{{ entry.message }}</span>
            <span v-if="transcriptTimeLabel(entry.createdAt)" class="region-copy">
              {{ transcriptTimeLabel(entry.createdAt) }}
            </span>
          </li>
        </ul>
      </div>

      <p v-if="showDegradedBanner" class="region-copy region-copy--degraded">
        {{ degradedBannerLabel }}
      </p>

      <button type="button" class="briefing-panel__cta" @click="emit('openChat')">
        <span class="briefing-panel__cta-icon" aria-hidden="true">◌</span>
        OPEN KAIRO CHAT
      </button>
    </template>
  </div>
</template>

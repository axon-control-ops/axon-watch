<script setup lang="ts">
import { computed } from 'vue';

import {
  kairoPresenceSubtitle,
  type KairoPresenceState,
} from '../lib/kairo-presence';
import OperatorPersonaMark from './OperatorPersonaMark.vue';

const props = defineProps<{
  state: KairoPresenceState;
  /** When set (employee thread active), mark/title reflect that teammate. */
  personaMark?: string | null;
  personaName?: string | null;
  /** Optional suffix when chip state needs extra context (e.g. failed shift). */
  presenceHint?: string | null;
  /** Warm red accent when alerting reflects a failed teammate shift. */
  employeeFailed?: boolean;
  /** Amber accent when alerting reflects an interrupted shift that can continue. */
  employeeInterrupted?: boolean;
  /** Overrides default briefing title when set (e.g. full failure detail on hover). */
  chipTitle?: string | null;
  /** Tooltip when the chip opens something other than briefing (e.g. team roster). */
  openHint?: string | null;
}>();

const emit = defineEmits<{
  openBriefing: [];
}>();

const subtitle = computed(() => kairoPresenceSubtitle(props.state));
const titleLabel = computed(() => {
  const name = props.personaName?.trim();
  const hint = props.presenceHint?.trim();
  if (name && hint) {
    return `${name} · ${hint}`;
  }
  if (name) {
    return name;
  }
  if (hint) {
    return hint;
  }
  return subtitle.value;
});
const showWaveform = computed(
  () =>
    props.state === 'observing' ||
    props.state === 'listening' ||
    props.state === 'speaking' ||
    props.state === 'thinking' ||
    props.state === 'alerting',
);
const accessibilityLabel = computed(() => {
  const detail = props.chipTitle?.trim() || props.openHint?.trim();
  if (props.employeeFailed && detail) {
    return `${titleLabel.value}. ${detail}`;
  }
  return `${titleLabel.value} presence`;
});
</script>

<template>
  <button
    type="button"
    class="kairo-chip"
    :class="[
      `kairo-chip--${state}`,
      {
        'kairo-chip--employee-failed':
          employeeFailed && !employeeInterrupted && state === 'alerting',
        'kairo-chip--employee-interrupted':
          employeeFailed && employeeInterrupted && state === 'alerting',
      },
    ]"
    :aria-label="accessibilityLabel"
    :title="chipTitle?.trim() || openHint?.trim() || 'Open operator briefing'"
    @click="emit('openBriefing')"
  >
    <span class="kairo-chip__pulse" aria-hidden="true" />
    <span v-if="showWaveform" class="kairo-chip__waveform" aria-hidden="true">
      <span />
      <span />
      <span />
      <span />
    </span>
    <span class="kairo-chip__label persona-title">
      <OperatorPersonaMark size="xs" :mark="personaMark" />
      <span class="kairo-chip__subtitle">{{ titleLabel }}</span>
    </span>
  </button>
</template>

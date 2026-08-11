<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue';

import type { CompanyEmployeeRecord } from '../../contracts/canonical';
import { buildEmployeeAvatar } from '../../features/workspace-agents/employee-avatar';
import {
  adjacentPresenceStripEmployee,
  COMPANY_ROSTER_DOCK_ID,
  employeeFailureLine,
  employeePresenceSelectAriaLabel,
  employeePresenceStripHoverTitle,
  employeeShiftNeedsContinuation,
  presenceStripOptionId,
  selectedPresenceStripEmployee,
  sortEmployeesForPresenceStrip,
} from '../../features/workspace-agents/company-roster-view';

const props = defineProps<{
  employees: CompanyEmployeeRecord[];
  selectedEmployeeId: string | null;
  /** Employee ids currently mid IDE/agent stream (client-side busy overlay). */
  liveBusyEmployeeIds?: readonly string[];
  /** Manual/Semi handoff waiters — amber glow until Start now. */
  handoffWaitingEmployeeIds?: readonly string[];
}>();

const emit = defineEmits<{
  select: [employee: CompanyEmployeeRecord];
}>();

const stripRef = ref<HTMLElement | null>(null);

const liveBusySet = computed(() => new Set(props.liveBusyEmployeeIds ?? []));
const handoffWaitingSet = computed(() => new Set(props.handoffWaitingEmployeeIds ?? []));

const items = computed(() => {
  const next = sortEmployeesForPresenceStrip(props.employees).map((employee) => {
    const liveBusy = liveBusySet.value.has(employee.employee_id);
    const handoffWaiting = !liveBusy && handoffWaitingSet.value.has(employee.employee_id);
    const failed = Boolean(employeeFailureLine(employee, { liveBusy }));
    const avatar = buildEmployeeAvatar(employee, { liveBusy, handoffWaiting });
    const interrupted = failed && employeeShiftNeedsContinuation(employee);
    const paused = !employee.enabled && !failed && !liveBusy;
    const working = avatar.presence === 'working' || liveBusy;
    const handoff = avatar.presence === 'handoff' || handoffWaiting;
    const approval = avatar.presence === 'approval';
    let presenceLabel = 'Idle';
    if (approval) {
      presenceLabel = 'Action needed';
    } else if (working) {
      presenceLabel = 'Busy';
    } else if (handoff) {
      presenceLabel = 'Handoff';
    } else if (interrupted) {
      presenceLabel = 'Retry';
    } else if (failed) {
      presenceLabel = 'Failed';
    } else if (paused) {
      presenceLabel = 'Paused';
    } else if (avatar.lead) {
      presenceLabel = 'Lead';
    }
    return {
      employee,
      avatar,
      failed,
      interrupted,
      paused,
      working,
      handoff,
      approval,
      presenceLabel,
      optionId: presenceStripOptionId(employee.employee_id),
    };
  });
  return next;
});

const activeOptionId = computed(() => presenceStripOptionId(props.selectedEmployeeId));

function scrollSelectedIntoView(): void {
  const optionId = activeOptionId.value;
  if (!optionId) {
    return;
  }
  void nextTick(() => {
    const root = stripRef.value;
    if (!root) {
      return;
    }
    const target = root.querySelector<HTMLElement>(`#${CSS.escape(optionId)}`);
    if (!target) {
      return;
    }
    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    target.scrollIntoView({
      block: 'nearest',
      inline: 'nearest',
      behavior: reducedMotion ? 'auto' : 'smooth',
    });
  });
}

watch(
  () => props.selectedEmployeeId,
  () => {
    scrollSelectedIntoView();
  },
  { immediate: true },
);

function focusEmployee(employeeId: string | null | undefined): void {
  if (!presenceStripOptionId(employeeId)) {
    return;
  }
  void nextTick(() => {
    stripRef.value?.focus();
  });
}

defineExpose({ focusEmployee });

/** Vertical wheel / trackpad → horizontal scroll when the strip overflows. */
function handleStripWheel(event: WheelEvent): void {
  const scroller = stripRef.value;
  if (!scroller) {
    return;
  }
  if (scroller.scrollWidth <= scroller.clientWidth + 1) {
    return;
  }
  const delta =
    Math.abs(event.deltaX) > Math.abs(event.deltaY) ? event.deltaX : event.deltaY;
  if (!delta) {
    return;
  }
  event.preventDefault();
  scroller.scrollLeft += delta;
}

function onKeydown(event: KeyboardEvent): void {
  if (event.key === 'Enter' || event.key === ' ') {
    const current = selectedPresenceStripEmployee(props.employees, props.selectedEmployeeId);
    if (current) {
      event.preventDefault();
      emit('select', current);
    }
    return;
  }

  const move =
    event.key === 'ArrowLeft' || event.key === 'ArrowUp'
      ? 'prev'
      : event.key === 'ArrowRight' || event.key === 'ArrowDown'
        ? 'next'
        : event.key === 'Home'
          ? 'first'
          : event.key === 'End'
            ? 'last'
            : null;
  if (!move) {
    return;
  }
  event.preventDefault();
  const next = adjacentPresenceStripEmployee(
    props.employees,
    props.selectedEmployeeId,
    move,
  );
  if (next) {
    emit('select', next);
  }
}
</script>

<template>
  <ul
    ref="stripRef"
    class="company-presence-strip"
    aria-label="Team presence"
    role="listbox"
    aria-multiselectable="false"
    aria-orientation="horizontal"
    :aria-activedescendant="activeOptionId || undefined"
    :aria-controls="COMPANY_ROSTER_DOCK_ID"
    tabindex="0"
    @keydown="onKeydown"
    @wheel="handleStripWheel"
  >
    <li v-for="item in items" :key="item.employee.employee_id" role="presentation">
      <button
        :id="item.optionId"
        type="button"
        class="company-presence-strip__btn"
        role="option"
        tabindex="-1"
        :class="{
          'company-presence-strip__btn--selected':
            selectedEmployeeId === item.employee.employee_id,
          'company-presence-strip__btn--busy': item.working,
          'company-presence-strip__btn--handoff': item.handoff,
          'company-presence-strip__btn--approval': item.approval,
          'company-presence-strip__btn--lead': item.avatar.lead,
        }"
        :data-presence="item.avatar.presence"
        :aria-selected="selectedEmployeeId === item.employee.employee_id ? 'true' : 'false'"
        :aria-label="employeePresenceSelectAriaLabel(item.employee)"
        :title="employeePresenceStripHoverTitle(item.employee)"
        @mousedown.prevent
        @click="emit('select', item.employee)"
      >
        <span
          class="company-presence-strip__avatar"
          :style="{
            background: item.avatar.background,
            color: item.avatar.foreground,
          }"
          :data-glow="item.avatar.glow"
          :data-presence="item.avatar.presence"
          :data-lead="item.avatar.lead ? 'true' : undefined"
        >
          <span
            v-if="item.working || item.handoff || item.approval"
            class="company-presence-strip__busy-ring"
            :class="{
              'company-presence-strip__busy-ring--handoff': item.handoff && !item.working,
              'company-presence-strip__busy-ring--approval': item.approval,
            }"
            aria-hidden="true"
          />
          <img
            class="company-presence-strip__face"
            :src="item.avatar.faceUrl"
            :alt="item.employee.name"
            width="28"
            height="28"
          >
          <span class="company-presence-strip__initials" aria-hidden="true">{{ item.avatar.initials }}</span>
          <span
            v-if="item.avatar.lead"
            class="company-presence-strip__lead-mark"
            aria-hidden="true"
            title="Lead"
          >
            ★
          </span>
          <span
            v-if="item.approval"
            class="company-presence-strip__approval-mark"
            aria-hidden="true"
            title="Action needed"
          >
            !
          </span>
          <span
            v-else-if="item.working"
            class="company-presence-strip__busy-mark"
            aria-hidden="true"
            title="Busy"
          >
            ●
          </span>
          <span
            v-else-if="item.interrupted"
            class="company-presence-strip__interrupt-mark"
            aria-hidden="true"
            title="Job interrupted — retry to continue"
          >
            ↻
          </span>
          <span
            v-else-if="item.failed"
            class="company-presence-strip__fail-mark"
            aria-hidden="true"
            title="Last job failed"
          >
            !
          </span>
          <span
            v-else-if="item.paused"
            class="company-presence-strip__pause-mark"
            aria-hidden="true"
            title="Paused"
          >
            ⏸
          </span>
        </span>
        <span class="company-presence-strip__name">{{ item.employee.name }}</span>
        <span
          class="company-presence-strip__role"
          :class="{
            'company-presence-strip__role--busy': item.working,
            'company-presence-strip__role--failed': item.failed && !item.working,
            'company-presence-strip__role--paused': item.paused,
          }"
        >
          {{ item.presenceLabel }}
        </span>
      </button>
    </li>
  </ul>
</template>

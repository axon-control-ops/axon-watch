<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue';

import AgentPersonaDock from './AgentPersonaDock.vue';
import CompanyPresenceStrip from './CompanyPresenceStrip.vue';
import { resolveRosterSelectionForIdeThread } from '../../features/workspace-agents/active-ide-employee';
import {
  buildCompanyRosterAlertBadge,
  companyBusyEmployeesCount,
  companyHeadline,
  companyFailedEmployeesHint,
  companyFailedEmployeesHintTooltip,
  companyHasFailedEmployees,
  COMPANY_ROSTER_DOCK_ID,
  employeeFailureLine,
  employeeIsActivelyBusy,
  employeeSpeakLine,
  firstFailedRosterEmployee,
  pickDefaultRosterEmployee,
} from '../../features/workspace-agents/company-roster-view';
import {
  markIntroSpokenToday,
  resolveTalkSpeakMode,
} from '../../features/workspace-agents/company-roster-intro-prefs';
import {
  employeeComposerOpenPayload,
  employeeQuickActions,
  type TeamMemberChatKind,
  type TeamMemberQuickAction,
  type TeamMemberSurfaceAction,
} from '../../features/workspace-agents/company-roster-actions';
import { patchWorkspaceEmployeeEnabled } from '../../api/worker-scheduler-api';
import { stopRun } from '../../api/runs-api';
import type { CompanyEmployeeRecord } from '../../contracts/canonical';
import { focusAgentDockComposerInput } from '../../lib/agent-dock-composer-focus';
import { requestIdeComposerMode } from '../../lib/ide-composer-restore-request';
import { employeeVoiceSpeaker } from '../../lib/kairo-voice-utterance';
import { navigateToSettingsSection } from '../../lib/settings-section-route';
import { useShellStore } from '../../stores/shell';

const shell = useShellStore();
const currentWorkspaceId = computed(() => shell.currentWorkspace?.workspace_id ?? null);
/** Single roster source of truth — shell owns the poll; do not dual-poll here (causes IDE flicker). */
const employees = computed(() => shell.companyEmployeesForCurrentWorkspace);
const loadState = computed<'idle' | 'loading' | 'loaded'>(() => {
  if (!currentWorkspaceId.value) {
    return 'idle';
  }
  return employees.value.length ? 'loaded' : 'idle';
});
const loadError = computed(() => null as string | null);

async function loadCompany(): Promise<void> {
  const workspaceId = currentWorkspaceId.value;
  if (!workspaceId) {
    return;
  }
  await shell.loadCompanyEmployees(workspaceId);
}
const selectedEmployeeId = ref<string | null>(null);
const dockRootRef = ref<HTMLElement | null>(null);
const presenceStripRef = ref<{ focusEmployee: (employeeId: string | null | undefined) => void } | null>(
  null,
);
const controlBusyId = ref<string | null>(null);
const controlError = ref<string | null>(null);

function scrollDockIntoView(): void {
  void nextTick(() => {
    const target = dockRootRef.value;
    if (!target) {
      return;
    }
    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    target.scrollIntoView({ block: 'nearest', behavior: reducedMotion ? 'auto' : 'smooth' });
  });
}

watch(currentWorkspaceId, () => {
  selectedEmployeeId.value = null;
});

watch(
  () => shell.activeIdeThread?.employee_id ?? null,
  (threadEmployeeId) => {
    if (!employees.value.length) {
      return;
    }
    const nextSelection = resolveRosterSelectionForIdeThread({
      threadEmployeeId,
      employees: employees.value,
      currentSelectionId: selectedEmployeeId.value,
    });
    if (nextSelection === selectedEmployeeId.value) {
      return;
    }
    selectedEmployeeId.value = nextSelection;
    const row = employees.value.find((entry) => entry.employee_id === nextSelection);
    if (row && employeeFailureLine(row)) {
      scrollDockIntoView();
    }
  },
);

watch(
  [employees, loadState],
  () => {
    if (loadState.value !== 'loaded' || !employees.value.length) {
      return;
    }
    if (selectedEmployeeId.value) {
      const stillPresent = employees.value.some(
        (row) => row.employee_id === selectedEmployeeId.value,
      );
      if (stillPresent) {
        return;
      }
      selectedEmployeeId.value = null;
    }
    const next = pickDefaultRosterEmployee(employees.value);
    if (next) {
      selectedEmployeeId.value = next.employee_id;
      if (employeeFailureLine(next)) {
        scrollDockIntoView();
      }
    }
  },
  { immediate: true },
);

watch(
  () => shell.teamRosterRevealToken,
  () => {
    if (!employees.value.length) {
      return;
    }
    const nextSelection = resolveRosterSelectionForIdeThread({
      threadEmployeeId: shell.activeIdeThread?.employee_id ?? null,
      employees: employees.value,
      currentSelectionId: selectedEmployeeId.value,
    });
    if (nextSelection && nextSelection !== selectedEmployeeId.value) {
      selectedEmployeeId.value = nextSelection;
    }
    const row = selectedEmployee.value;
    if (!row) {
      return;
    }
    presenceStripRef.value?.focusEmployee(row.employee_id);
    scrollDockIntoView();
  },
);

const headline = computed(() =>
  companyHeadline(
    shell.currentWorkspace?.display_name ?? shell.currentWorkspace?.workspace_id,
    employees.value.length,
  ),
);

const hasFailedEmployees = computed(() => companyHasFailedEmployees(employees.value));

const rosterAlertBadge = computed(() => buildCompanyRosterAlertBadge(employees.value));

const liveBusyEmployeeIds = computed(() => {
  const ids = new Set<string>();
  for (const row of employees.value) {
    if (employeeIsActivelyBusy(row)) {
      ids.add(row.employee_id);
    }
  }
  // Prefer the open IDE thread's owner — Lead can be "delegating" in chrome while
  // a specialist thread is the one actually streaming.
  if (shell.agentStreamActive) {
    const threadEmployeeId = shell.activeIdeThread?.employee_id?.trim();
    const recordEmployeeId = shell.activeIdeEmployeeRecord?.employee_id?.trim();
    const streamOwnerId = threadEmployeeId || recordEmployeeId;
    if (streamOwnerId) {
      ids.add(streamOwnerId);
    }
  }
  // #region agent log
  fetch('http://127.0.0.1:7706/ingest/90bcaec2-2b39-4d4a-84b5-157c12735440', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Debug-Session-Id': 'fc0b35',
    },
    body: JSON.stringify({
      sessionId: 'fc0b35',
      runId: 'busy-owner',
      hypothesisId: 'H9',
      location: 'CompanyRosterPanel.vue:liveBusyEmployeeIds',
      message: 'team busy owners resolved',
      data: {
        busyIds: [...ids],
        streamActive: Boolean(shell.agentStreamActive),
        threadEmployeeId: shell.activeIdeThread?.employee_id ?? null,
        recordEmployeeId: shell.activeIdeEmployeeRecord?.employee_id ?? null,
        rosterBusy: employees.value
          .filter((row) => employeeIsActivelyBusy(row))
          .map((row) => ({ id: row.employee_id, name: row.name, status: row.status })),
        leadStatus: employees.value.find((row) => row.role === 'lead')?.status ?? null,
      },
      timestamp: Date.now(),
    }),
  }).catch(() => {});
  // #endregion
  return [...ids];
});

const busyCount = computed(() => {
  const rosterBusy = companyBusyEmployeesCount(employees.value);
  const liveExtra = liveBusyEmployeeIds.value.filter(
    (id) => !employees.value.some((row) => row.employee_id === id && employeeIsActivelyBusy(row)),
  ).length;
  return rosterBusy + liveExtra;
});

const busyBadgeLabel = computed(() => {
  const count = busyCount.value;
  if (count <= 0) {
    return null;
  }
  return `${count} BUSY`;
});

const failedEmployeesHint = computed(() => companyFailedEmployeesHint(employees.value));

const failedEmployeesHintTooltip = computed(() =>
  companyFailedEmployeesHintTooltip(employees.value),
);

const selectedEmployee = computed(
  () => employees.value.find((row) => row.employee_id === selectedEmployeeId.value) ?? null,
);

const selectedActions = computed(() =>
  selectedEmployee.value ? employeeQuickActions(selectedEmployee.value) : [],
);

function selectEmployee(employee: CompanyEmployeeRecord): void {
  selectedEmployeeId.value = employee.employee_id;
}

function speakEmployeeLine(employee: CompanyEmployeeRecord, kind: TeamMemberChatKind): void {
  if (kind !== 'talk' && kind !== 'status') {
    return;
  }
  if (kind === 'status') {
    const line = employeeSpeakLine(employee, 'status');
    void shell.speakKairoConversationLine(line, {
      operatorPrompt: `Teammate ${employee.name}`,
      skipSpeakApi: true,
      azureVoiceId: employee.azure_voice_id,
      speaker: employeeVoiceSpeaker(employee),
    });
    return;
  }

  const talkMode = resolveTalkSpeakMode(employee.employee_id);
  const line = employeeSpeakLine(employee, 'talk', {
    talkMode,
    entropy: String(Date.now()),
  });
  if (talkMode === 'intro') {
    markIntroSpokenToday(employee.employee_id);
  }
  void shell.speakKairoConversationLine(line, {
    operatorPrompt: `Teammate ${employee.name}`,
    skipSpeakApi: true,
    azureVoiceId: employee.azure_voice_id,
    speaker: employeeVoiceSpeaker(employee),
  });
}

async function startChat(employee: CompanyEmployeeRecord, kind: TeamMemberChatKind): Promise<void> {
  selectEmployee(employee);
  // Talk / Status / Assign / Retry all land on that teammate's owned IDE thread.
  await shell.openOrFocusEmployeeIdeThread(employee);
  const { mode, draft } = employeeComposerOpenPayload(employee, kind);
  requestIdeComposerMode(mode);
  if (draft) {
    shell.openIdeComposerWithDraft(draft, { keepActivityView: true });
  } else {
    shell.openIdeComposer({ keepActivityView: true });
  }
  focusAgentDockComposerInput();
  speakEmployeeLine(employee, kind);
}

function openSurface(surface: TeamMemberSurfaceAction): void {
  if (shell.layoutMode !== 'ide') {
    shell.setLayoutMode('ide');
  }
  if (surface === 'attention') {
    shell.focusAttentionSidebar();
    return;
  }
  shell.focusKairoBriefing();
}

async function onControlAction(
  employee: CompanyEmployeeRecord,
  action: TeamMemberQuickAction,
): Promise<void> {
  if (action.control === 'toggle_enabled') {
    const workspaceId = currentWorkspaceId.value?.trim();
    if (!workspaceId) {
      return;
    }
    controlBusyId.value = employee.employee_id;
    controlError.value = null;
    try {
      await patchWorkspaceEmployeeEnabled(workspaceId, employee.employee_id, !employee.enabled);
      await loadCompany();
    } catch (error) {
      controlError.value =
        error instanceof Error ? error.message : 'Could not update agent enabled state';
    } finally {
      controlBusyId.value = null;
    }
    return;
  }
  if (action.control === 'stop') {
    const runId = employee.active_run_id?.trim();
    if (!runId) {
      return;
    }
    controlBusyId.value = employee.employee_id;
    controlError.value = null;
    try {
      await stopRun(runId);
      await loadCompany();
    } catch (error) {
      controlError.value = error instanceof Error ? error.message : 'Could not stop shift';
    } finally {
      controlBusyId.value = null;
    }
  }
}

function onQuickAction(employee: CompanyEmployeeRecord, action: TeamMemberQuickAction): void {
  if (action.kind === 'control') {
    void onControlAction(employee, action);
    return;
  }
  if (action.kind === 'surface' && action.surface) {
    selectEmployee(employee);
    openSurface(action.surface);
    return;
  }
  if (action.chatKind) {
    void startChat(employee, action.chatKind);
  }
}

function openFleetSettings(): void {
  navigateToSettingsSection('agents');
}

async function focusFailedEmployee(): Promise<void> {
  const target = firstFailedRosterEmployee(employees.value);
  if (!target) {
    return;
  }
  selectEmployee(target);
  presenceStripRef.value?.focusEmployee(target.employee_id);
  await shell.openOrFocusEmployeeIdeThread(target);
  scrollDockIntoView();
}

async function onPresenceSelect(employee: CompanyEmployeeRecord): Promise<void> {
  selectEmployee(employee);
  if (employeeFailureLine(employee)) {
    await shell.openOrFocusEmployeeIdeThread(employee);
    scrollDockIntoView();
  }
}
</script>

<template>
  <section
    v-if="currentWorkspaceId"
    class="company-roster company-roster--ide company-roster--persona-dock"
    aria-label="Company employees"
  >
    <header class="company-roster__header">
      <div class="company-roster__header-row">
        <div>
          <p class="company-roster__eyebrow">Company team</p>
          <h3 class="company-roster__title">
            {{ headline }}
            <button
              v-if="rosterAlertBadge"
              type="button"
              class="company-roster__alert-badge"
              :class="{
                'company-roster__alert-badge--interrupted':
                  rosterAlertBadge.tone === 'interrupted',
                'company-roster__alert-badge--mixed': rosterAlertBadge.tone === 'mixed',
              }"
              :title="rosterAlertBadge.title"
              :aria-label="rosterAlertBadge.ariaLabel"
              @click="focusFailedEmployee"
            >
              {{ rosterAlertBadge.label }}
            </button>
            <span
              v-if="busyBadgeLabel"
              class="company-roster__busy-badge"
              :title="`${busyCount} teammate${busyCount === 1 ? '' : 's'} currently busy`"
              :aria-label="`${busyCount} teammate${busyCount === 1 ? '' : 's'} currently busy`"
            >
              {{ busyBadgeLabel }}
            </span>
          </h3>
        </div>
        <button
          v-if="employees.length"
          type="button"
          class="company-roster__fleet-link"
          aria-label="Open agent fleet settings"
          @click="openFleetSettings"
        >
          Fleet controls
        </button>
      </div>
      <button
        v-if="hasFailedEmployees && failedEmployeesHint"
        type="button"
        class="company-roster__hint company-roster__hint--alert company-roster__hint--action"
        :title="failedEmployeesHintTooltip ?? undefined"
        @click="focusFailedEmployee"
      >
        {{ failedEmployeesHint }}
      </button>
      <p v-else class="company-roster__hint">
        Select a teammate below to open their dock. Talk for a check-in; first click of the day is an intro.
      </p>
    </header>

    <p v-if="loadState === 'loading' && !employees.length" class="company-roster__empty">
      Loading team…
    </p>
    <p v-else-if="loadError" class="company-roster__empty company-roster__empty--error">
      {{ loadError }}
    </p>
    <p v-else-if="!employees.length" class="company-roster__empty">
      No employees staffed yet.
    </p>

    <template v-else>
      <p v-if="controlError" class="company-roster__empty company-roster__empty--error">
        {{ controlError }}
      </p>

      <CompanyPresenceStrip
        ref="presenceStripRef"
        :employees="employees"
        :selected-employee-id="selectedEmployeeId"
        :live-busy-employee-ids="liveBusyEmployeeIds"
        @select="onPresenceSelect"
      />

      <div :id="COMPANY_ROSTER_DOCK_ID" ref="dockRootRef" class="company-roster__dock-host">
        <AgentPersonaDock
          v-if="selectedEmployee"
          :key="selectedEmployee.employee_id"
          :employee="selectedEmployee"
          :actions="selectedActions"
          :control-busy="controlBusyId === selectedEmployee.employee_id"
          @talk="void startChat(selectedEmployee, 'talk')"
          @action="onQuickAction(selectedEmployee, $event)"
        />
      </div>
    </template>
  </section>
</template>

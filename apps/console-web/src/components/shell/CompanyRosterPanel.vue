<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue';

import { useWorkspaceCompany } from '../../features/workspace-agents/use-workspace-company';
import { resolveRosterSelectionForIdeThread } from '../../features/workspace-agents/active-ide-employee';
import {
  companyFailedEmployees,
  companyFailedEmployeesHint,
  companyHasFailedEmployees,
  companyHeadline,
  employeeFailureLine,
  employeeGlowTone,
  employeeIsWorking,
  employeeMetaLine,
  employeeSpeakLine,
  employeeStatusLabel,
  employeeTalkLine,
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
import { navigateToSettingsSection } from '../../lib/settings-section-route';
import { useShellStore } from '../../stores/shell';

const shell = useShellStore();
const currentWorkspaceId = computed(() => shell.currentWorkspace?.workspace_id ?? null);
const { company, employees, loadState, loadError, loadCompany } =
  useWorkspaceCompany(currentWorkspaceId);
const selectedEmployeeId = ref<string | null>(null);
const listRootRef = ref<HTMLElement | null>(null);
const controlBusyId = ref<string | null>(null);
const controlError = ref<string | null>(null);

function scrollSelectedIntoView(): void {
  void nextTick(() => {
    const root = listRootRef.value;
    const id = selectedEmployeeId.value;
    if (!root || !id) {
      return;
    }
    const target = root.querySelector<HTMLElement>(`[data-employee-id="${CSS.escape(id)}"]`);
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
    scrollSelectedIntoView();
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
    scrollSelectedIntoView();
  },
);

const headline = computed(() =>
  companyHeadline(company.value?.company_name, company.value?.employee_count),
);

const hasFailedEmployees = computed(() => companyHasFailedEmployees(employees.value));
const failedEmployeeCount = computed(() => companyFailedEmployees(employees.value).length);
const failedEmployeesHint = computed(() => companyFailedEmployeesHint(employees.value));

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
      await loadCompany({ reason: 'employee-enabled' });
    } catch (error) {
      controlError.value =
        error instanceof Error ? error.message : 'Could not update agent enabled state';
    } finally {
      controlBusyId.value = null;
    }
    return;
  }

  if (action.control === 'stop_run') {
    const runId = employee.active_run_id?.trim();
    if (!runId) {
      return;
    }
    controlBusyId.value = employee.employee_id;
    controlError.value = null;
    try {
      await stopRun(runId);
      await loadCompany({ reason: 'employee-stop' });
      await shell.refreshRunSurfaces({ light: true });
    } catch (error) {
      controlError.value = error instanceof Error ? error.message : 'Could not stop active run';
    } finally {
      controlBusyId.value = null;
    }
  }
}

async function onRowActivate(employee: CompanyEmployeeRecord): Promise<void> {
  await startChat(employee, 'talk');
}

async function onQuickAction(
  employee: CompanyEmployeeRecord,
  action: TeamMemberQuickAction,
): Promise<void> {
  if (action.kind === 'control') {
    await onControlAction(employee, action);
    return;
  }
  if (action.kind === 'surface' && action.surface) {
    selectEmployee(employee);
    openSurface(action.surface);
    return;
  }
  if (action.chatKind) {
    await startChat(employee, action.chatKind);
  }
}

function focusFailedEmployee(): void {
  const target = firstFailedRosterEmployee(employees.value);
  if (!target) {
    return;
  }
  selectedEmployeeId.value = target.employee_id;
  scrollSelectedIntoView();
  void startChat(target, 'retry');
}

function openFleetSettings(): void {
  navigateToSettingsSection('agent-fleet');
}

function rowClasses(employee: CompanyEmployeeRecord): Record<string, boolean> {
  const working = employeeIsWorking(employee.status);
  return {
    'company-roster__row--primary': employee.primary,
    'company-roster__row--selected': selectedEmployeeId.value === employee.employee_id,
    'company-roster__row--working': working,
    'company-roster__row--failed': Boolean(employeeFailureLine(employee)),
    [`company-roster__row--${employee.role}`]: true,
    [`company-roster__row--glow-${employeeGlowTone(employee)}`]: working,
    [`company-roster__row--status-${employee.status}`]: working,
  };
}
</script>

<template>
  <section
    v-if="currentWorkspaceId"
    class="company-roster company-roster--ide"
    aria-label="Company employees"
  >
    <header class="company-roster__header">
      <div class="company-roster__header-row">
        <div>
          <p class="company-roster__eyebrow">Company team</p>
          <h3 class="company-roster__title">
            {{ headline }}
            <button
              v-if="failedEmployeeCount"
              type="button"
              class="company-roster__alert-badge"
              :title="`${failedEmployeeCount} teammate${failedEmployeeCount === 1 ? '' : 's'} need attention after a failed shift`"
              :aria-label="`Jump to ${failedEmployeeCount} failed teammate${failedEmployeeCount === 1 ? '' : 's'}`"
              @click="focusFailedEmployee"
            >
              {{ failedEmployeeCount }} failed
            </button>
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
        @click="focusFailedEmployee"
      >
        {{ failedEmployeesHint }}
      </button>
      <p v-else class="company-roster__hint">
        Click a teammate to open their chat thread. First click of the day is an intro; later clicks get a quick check-in.
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

      <ul ref="listRootRef" class="company-roster__list">
        <li
          v-for="employee in employees"
          :key="employee.employee_id"
          class="company-roster__item"
          :data-employee-id="employee.employee_id"
          :class="{ 'company-roster__item--working': employeeIsWorking(employee.status) }"
        >
          <p
            v-if="employeeTalkLine(employee)"
            class="company-roster__talk"
            :class="[
              `company-roster__talk--${employeeGlowTone(employee)}`,
              { 'company-roster__talk--failed': !!employeeFailureLine(employee) },
            ]"
            :data-status="employeeFailureLine(employee) ? 'failed' : employee.status"
            :title="employee.last_outcome_detail || undefined"
          >
            {{ employeeTalkLine(employee) }}
          </p>
          <button
            type="button"
            class="company-roster__row"
            :class="rowClasses(employee)"
            :aria-pressed="selectedEmployeeId === employee.employee_id ? 'true' : 'false'"
            :aria-label="`Talk to ${employee.name}`"
            @click="onRowActivate(employee)"
          >
            <span class="company-roster__identity">
              <span class="company-roster__name">
                {{ employee.name }}
                <span v-if="employee.primary" class="company-roster__badge">Lead</span>
                <span
                  v-if="!employee.enabled"
                  class="company-roster__badge company-roster__badge--paused"
                >
                  Paused
                </span>
              </span>
              <span class="company-roster__meta">{{ employeeMetaLine(employee) }}</span>
              <span class="company-roster__owns">{{ employee.owns }}</span>
            </span>
            <span class="company-roster__status" :data-status="employee.status">
              {{ employeeStatusLabel(employee.status) }}
            </span>
          </button>

          <div
            v-if="selectedEmployeeId === employee.employee_id && selectedActions.length"
            class="company-roster__actions"
            role="group"
            :aria-label="`Actions for ${employee.name}`"
          >
            <button
              v-for="action in selectedActions"
              :key="action.id"
              type="button"
              class="company-roster__action"
              :class="{
                'company-roster__action--surface': action.kind === 'surface',
                'company-roster__action--retry': action.id === 'retry',
                'company-roster__action--receipts': action.id === 'receipts',
                'company-roster__action--control': action.kind === 'control',
              }"
              :disabled="controlBusyId === employee.employee_id && action.kind === 'control'"
              @click.stop="onQuickAction(employee, action)"
            >
              {{ action.label }}
            </button>
          </div>
        </li>
      </ul>
    </template>
  </section>
</template>

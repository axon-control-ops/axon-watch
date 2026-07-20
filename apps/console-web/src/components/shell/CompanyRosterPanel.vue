<script setup lang="ts">
import { computed, ref } from 'vue';

import { useWorkspaceCompany } from '../../features/workspace-agents/use-workspace-company';
import {
  companyHeadline,
  employeeFailureLine,
  employeeGlowTone,
  employeeIsWorking,
  employeeMetaLine,
  employeeSpeakLine,
  employeeStatusLabel,
  employeeTalkLine,
} from '../../features/workspace-agents/company-roster-view';
import {
  markIntroSpokenToday,
  resolveTalkSpeakMode,
} from '../../features/workspace-agents/company-roster-intro-prefs';
import {
  employeeChatComposerMode,
  employeeChatDraft,
  employeeQuickActions,
  type TeamMemberChatKind,
  type TeamMemberQuickAction,
  type TeamMemberSurfaceAction,
} from '../../features/workspace-agents/company-roster-actions';
import type { CompanyEmployeeRecord } from '../../contracts/canonical';
import { focusAgentDockComposerInput } from '../../lib/agent-dock-composer-focus';
import { requestIdeComposerMode } from '../../lib/ide-composer-restore-request';
import { useShellStore } from '../../stores/shell';

const shell = useShellStore();
const currentWorkspaceId = computed(() => shell.currentWorkspace?.workspace_id ?? null);
const { company, employees, loadState, loadError } = useWorkspaceCompany(currentWorkspaceId);
const selectedEmployeeId = ref<string | null>(null);

const headline = computed(() =>
  companyHeadline(company.value?.company_name, company.value?.employee_count),
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
  });
}

function startChat(employee: CompanyEmployeeRecord, kind: TeamMemberChatKind): void {
  selectEmployee(employee);
  requestIdeComposerMode(employeeChatComposerMode(kind));
  const draft = employeeChatDraft(employee, kind).trim();
  if (draft) {
    shell.openIdeComposerWithDraft(draft, { keepActivityView: true });
  } else {
    // Talk: open chat ready to type — no boilerplate line in the composer.
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

function onRowActivate(employee: CompanyEmployeeRecord): void {
  startChat(employee, 'talk');
}

function onQuickAction(employee: CompanyEmployeeRecord, action: TeamMemberQuickAction): void {
  if (action.kind === 'surface' && action.surface) {
    selectEmployee(employee);
    openSurface(action.surface);
    return;
  }
  if (action.chatKind) {
    startChat(employee, action.chatKind);
  }
}

function rowClasses(employee: CompanyEmployeeRecord): Record<string, boolean> {
  const working = employeeIsWorking(employee.status);
  return {
    'company-roster__row--primary': employee.primary,
    'company-roster__row--selected': selectedEmployeeId.value === employee.employee_id,
    'company-roster__row--working': working,
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
      <p class="company-roster__eyebrow">Company team</p>
      <h3 class="company-roster__title">{{ headline }}</h3>
      <p class="company-roster__hint">
        Click a teammate to open chat. First click of the day is an intro; later clicks get a quick check-in.
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

    <ul v-else class="company-roster__list">
      <li
        v-for="employee in employees"
        :key="employee.employee_id"
        class="company-roster__item"
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
            </span>
            <span class="company-roster__meta">{{ employeeMetaLine(employee) }}</span>
            <span class="company-roster__owns">{{ employee.owns }}</span>
          </span>
          <span
            class="company-roster__status"
            :data-status="employee.status"
          >
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
            }"
            @click.stop="onQuickAction(employee, action)"
          >
            {{ action.label }}
          </button>
        </div>
      </li>
    </ul>
  </section>
</template>

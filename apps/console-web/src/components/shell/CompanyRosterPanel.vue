<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue';

import AgentPersonaDock from './AgentPersonaDock.vue';
import CompanyPresenceStrip from './CompanyPresenceStrip.vue';
import RosterDecisionBadge from './RosterDecisionBadge.vue';
import VaxonRosterVoiceDock from './VaxonRosterVoiceDock.vue';
import {
  shouldShowVaxonRosterVoiceDock,
  useVaxonRosterVoiceDock,
} from '../../features/kairo-conversation/use-vaxon-roster-voice-dock';
import { resolveRosterSelectionForIdeThread } from '../../features/workspace-agents/active-ide-employee';
import {
  buildCompanyRosterAlertBadge,
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
  resolveLiveBusyEmployeeIds,
  resolveReportingEmployeeId,
} from '../../features/workspace-agents/company-roster-view';
import {
  markIntroSpokenToday,
  resolveTalkSpeakMode,
} from '../../features/workspace-agents/company-roster-intro-prefs';
import {
  employeeComposerOpenPayload,
  type TeamMemberChatKind,
  type TeamMemberQuickAction,
  type TeamMemberSurfaceAction,
} from '../../features/workspace-agents/company-roster-actions';
import type { CompanyEmployeeRecord } from '../../contracts/canonical';
import { focusAgentDockComposerInput } from '../../lib/agent-dock-composer-focus';
import { requestIdeComposerMode } from '../../lib/ide-composer-restore-request';
import { employeeVoiceSpeaker } from '../../lib/kairo-voice-utterance';
import { runEmployeeShiftRetry } from '../../lib/run-employee-shift-retry';
import { navigateToSettingsSection } from '../../lib/settings-section-route';
import { buildPendingDecisionComposerDraft, companyPendingDecisionHint } from '../../features/workspace-agents/company-roster-focus';
import { submitQuestionAnswer } from '../../lib/submit-question-answer';
import { useCompanyRosterControlActions } from '../../composables/use-company-roster-control-actions';
import { useCompanyRosterQuickActionState } from '../../composables/use-company-roster-quick-action-state';
import { useShellStore } from '../../stores/shell';
const shell = useShellStore();
const currentWorkspaceId = computed(() => shell.currentWorkspace?.workspace_id ?? null);
const vaxonVoiceDock = useVaxonRosterVoiceDock(
  computed(() => shell.kairoSpeechActive),
  currentWorkspaceId,
);
const showVaxonVoiceDock = computed(() =>
  shouldShowVaxonRosterVoiceDock({
    layoutMode: shell.layoutMode,
    operatorBrainGalaxyActive: shell.operatorBrainGalaxyActive,
    operatorCenterView: shell.operatorCenterView,
    voiceDockVisible: vaxonVoiceDock.visible.value,
  }),
);
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
const { controlBusyId, controlError, onControlAction } = useCompanyRosterControlActions({
  shell,
  currentWorkspaceId,
  loadCompany,
});

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
  { immediate: true },
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

// Shared by liveBusyEmployeeIds and selectedEmployeeIsReporting below —
// both need "whose thread is focused while a stream is active".
const focusedStreamEmployeeId = computed(() =>
  shell.agentStreamActive
    ? shell.activeIdeThread?.employee_id?.trim() ||
      shell.activeIdeEmployeeRecord?.employee_id?.trim() ||
      null
    : null,
);

const liveBusyEmployeeIds = computed(() =>
  resolveLiveBusyEmployeeIds({
    employees: employees.value,
    streamingThreadIds: shell.streamingIdeThreadIds,
    threads: shell.ideThreadsForCurrentWorkspace,
    focusedStreamEmployeeId: focusedStreamEmployeeId.value,
  }),
);

const hasFailedEmployees = computed(() =>
  companyHasFailedEmployees(employees.value, liveBusyEmployeeIds.value),
);

const rosterAlertBadge = computed(() =>
  buildCompanyRosterAlertBadge(employees.value, liveBusyEmployeeIds.value),
);

const busyCount = computed(() => liveBusyEmployeeIds.value.length);

const pendingDecisionEmployees = computed(() => employees.value.filter((employee) => employee.pending_decision_id));

const pendingDecisionHint = computed(() => companyPendingDecisionHint(employees.value));

const busyBadgeLabel = computed(() => {
  if (!employees.value.length) {
    return null;
  }
  return `${busyCount.value} BUSY`;
});

const failedEmployeesHint = computed(() =>
  companyFailedEmployeesHint(employees.value, liveBusyEmployeeIds.value),
);

const failedEmployeesHintTooltip = computed(() =>
  companyFailedEmployeesHintTooltip(employees.value, liveBusyEmployeeIds.value),
);

const selectedEmployee = computed(
  () => employees.value.find((row) => row.employee_id === selectedEmployeeId.value) ?? null,
);

// True only while the SELECTED teammate's own thread is the one live-streaming.
// The dock shows that live report in place; the team header and presence strip remain
// available so the operator can still see and switch between the rest of the roster.
const selectedEmployeeIsReporting = computed(
  () =>
    Boolean(selectedEmployee.value) &&
    resolveReportingEmployeeId({
      agentStreamActive: shell.agentStreamActive,
      activeThreadEmployeeId: focusedStreamEmployeeId.value,
      streamingThreadIds: shell.streamingIdeThreadIds,
      threads: shell.ideThreadsForCurrentWorkspace,
    }) === selectedEmployee.value?.employee_id,
);

const { selectedActions, handoffWaitingEmployeeIds, selectedHandoffBlockedReason } =
  useCompanyRosterQuickActionState({
  shell,
  employees,
  selectedEmployee,
  liveBusyEmployeeIds,
});

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
  if (kind === 'retry') {
    controlError.value = null;
    const result = await runEmployeeShiftRetry(shell, employee, {
      keepActivityView: true,
      focusThread: true,
    });
    if (!result.ok) {
      controlError.value = result.reason;
      return;
    }
    speakEmployeeLine(employee, kind);
    return;
  }
  // Talk / Status / Assign land on that teammate's owned IDE thread.
  await shell.openOrFocusEmployeeIdeThread(employee);
  const { mode, draft } = employeeComposerOpenPayload(employee, kind);
  // Status is voice + focus only — never flip Ask/consultative (or any mode).
  if (mode) {
    requestIdeComposerMode(mode);
  }
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
  shell.openIdeComposer({ keepActivityView: true });
  focusAgentDockComposerInput();
  scrollDockIntoView();
}

async function focusPendingDecisionEmployee(employee?: CompanyEmployeeRecord): Promise<void> {
  const target = employee?.pending_decision_id ? employee : pendingDecisionEmployees.value[0];
  if (!target) {
    return;
  }
  selectEmployee(target);
  presenceStripRef.value?.focusEmployee(target.employee_id);

  shell.setIdeActivityView('agent');
  const threadId = await shell.openOrFocusEmployeeIdeThread(target);
  if (!threadId) {
    shell.commandMutationError = 'Could not open the teammate thread for this decision.';
    return;
  }

  const draft = buildPendingDecisionComposerDraft(target);
  if (draft) {
    shell.openIdeComposerWithDraft(draft, { keepActivityView: true });
  } else {
    shell.openIdeComposer({ keepActivityView: true });
  }
  focusAgentDockComposerInput();
  scrollDockIntoView();
}

async function applyPendingDecisionOption(
  employee: CompanyEmployeeRecord,
  option: { id: string; label: string },
): Promise<void> {
  if (!employee.pending_decision_id || !option.id?.trim()) {
    return;
  }
  selectEmployee(employee);
  presenceStripRef.value?.focusEmployee(employee.employee_id);
  shell.setIdeActivityView('agent');
  const threadId = await shell.openOrFocusEmployeeIdeThread(employee);
  if (!threadId) {
    shell.commandMutationError = 'Could not open the teammate thread for this decision.';
    return;
  }
  await submitQuestionAnswer(shell, {
    workspaceId: currentWorkspaceId.value,
    option,
    prompt:
      employee.pending_decision_prompt?.trim()
      || employee.pending_decision_title?.replace(/^.+? needs a decision:\s*/i, '').trim()
      || undefined,
  });
  focusAgentDockComposerInput();
  scrollDockIntoView();
}

async function recoverSelectedEmployeeFailure(): Promise<void> {
  const target = selectedEmployee.value;
  if (!target || !employeeFailureLine(target)) {
    return;
  }
  await startChat(target, 'retry');
}

async function onPresenceSelect(employee: CompanyEmployeeRecord): Promise<void> {
  selectEmployee(employee);
  // Busy fan-out specialists write into their own IDE thread — selecting them must
  // open/refetch that dock, not leave the operator on Dana's stale conversation.
  await shell.openOrFocusEmployeeIdeThread(employee);
  scrollDockIntoView();
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
              :class="{ 'company-roster__busy-badge--idle': busyCount === 0 }"
              :title="`${busyCount} teammate${busyCount === 1 ? '' : 's'} currently busy`"
              :aria-label="`${busyCount} teammate${busyCount === 1 ? '' : 's'} currently busy`"
            >
              {{ busyBadgeLabel }}
            </span>
            <RosterDecisionBadge
              :count="pendingDecisionEmployees.length"
              @open="focusPendingDecisionEmployee"
            />
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
        v-if="pendingDecisionHint"
        type="button"
        class="company-roster__hint company-roster__hint--alert company-roster__hint--action company-roster__hint--decision"
        @click="focusPendingDecisionEmployee()"
      >
        {{ pendingDecisionHint }}
      </button>
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
      <p
        v-if="controlError"
        class="company-roster__empty company-roster__empty--error"
        role="alert"
      >
        {{ controlError }}
      </p>
      <p
        v-else-if="selectedHandoffBlockedReason"
        class="company-roster__empty company-roster__hint"
        role="status"
      >
        {{ selectedHandoffBlockedReason }}
      </p>

      <CompanyPresenceStrip
        ref="presenceStripRef"
        class="company-roster__presence-strip"
        :employees="employees"
        :selected-employee-id="selectedEmployeeId"
        :live-busy-employee-ids="liveBusyEmployeeIds"
        :handoff-waiting-employee-ids="handoffWaitingEmployeeIds"
        @select="onPresenceSelect"
      />

      <div :id="COMPANY_ROSTER_DOCK_ID" ref="dockRootRef" class="company-roster__dock-host">
        <!-- Mission Control uses the right LIVE OPERATIONS orb; IDE uses KairoSidebarPanel. -->
        <VaxonRosterVoiceDock
          v-if="showVaxonVoiceDock"
          :speaking="vaxonVoiceDock.speaking.value"
          :line="vaxonVoiceDock.line.value"
          :remaining-seconds="vaxonVoiceDock.remainingSeconds.value"
          :on-dismiss="vaxonVoiceDock.dismiss"
          :on-replied="vaxonVoiceDock.markReplied"
        />
        <AgentPersonaDock
          v-if="selectedEmployee"
          :key="selectedEmployee.employee_id"
          :employee="selectedEmployee"
          :actions="selectedActions"
          :control-busy="controlBusyId === selectedEmployee.employee_id"
          :live-busy="liveBusyEmployeeIds.includes(selectedEmployee.employee_id)"
          :handoff-waiting="handoffWaitingEmployeeIds.includes(selectedEmployee.employee_id)"
          :reporting="selectedEmployeeIsReporting"
          :transcript="selectedEmployeeIsReporting ? shell.latestWorkspaceAgentOutput ?? '' : ''"
          @talk="void startChat(selectedEmployee, 'talk')"
          @decision="void focusPendingDecisionEmployee(selectedEmployee)"
          @decision-option="void applyPendingDecisionOption(selectedEmployee, $event)"
          @recover-failure="void recoverSelectedEmployeeFailure()"
          @action="onQuickAction(selectedEmployee, $event)"
        />
      </div>
    </template>
  </section>
</template>

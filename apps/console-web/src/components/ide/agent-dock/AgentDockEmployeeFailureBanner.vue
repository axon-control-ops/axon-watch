<script setup lang="ts">
import { computed, ref } from 'vue';

import type { CompanyEmployeeRecord } from '../../../contracts/canonical';
import { employeeComposerOpenPayload } from '../../../features/workspace-agents/company-roster-actions';
import {
  employeeDockReceiptRunId,
  employeeFailureBannerAriaLabel,
  employeeFailureBannerCopy,
  employeeFailureDetailTooltip,
  employeeFailureRetryActionLabel,
  employeeShiftNeedsContinuation,
} from '../../../features/workspace-agents/company-roster-view';
import { focusAgentDockComposerInput } from '../../../lib/agent-dock-composer-focus';
import { requestIdeComposerMode } from '../../../lib/ide-composer-restore-request';
import { shouldSurfaceIdeEmployeeFailure } from '../../../lib/ide-presence-profile';
import { runEmployeeShiftRetry } from '../../../lib/run-employee-shift-retry';
import { useShellStore } from '../../../stores/shell';

const shell = useShellStore();
const retrying = ref(false);

const failureLine = computed(() => shell.activeIdeEmployeeFailureLine);
const employee = computed(() => shell.activeIdeEmployeeRecord);
const showBanner = computed(() =>
  shouldSurfaceIdeEmployeeFailure({
    profileState: shell.ideDisplayKairoPresenceState,
    employeeFailureLine: failureLine.value,
    agentStreamActive: shell.agentStreamActive,
    kairoSpeechActive: shell.kairoSpeechActive,
  }) && Boolean(employee.value),
);
const failureCopy = computed(() =>
  employee.value ? employeeFailureBannerCopy(employee.value) : '',
);
const failureDetailTooltip = computed(() =>
  employee.value ? employeeFailureDetailTooltip(employee.value) : undefined,
);
const failureAriaLabel = computed(() =>
  employee.value ? employeeFailureBannerAriaLabel(employee.value) : undefined,
);
const showReceiptsAction = computed(() =>
  employee.value ? Boolean(employeeDockReceiptRunId(employee.value)) : false,
);
const interruptedShift = computed(() =>
  employee.value ? employeeShiftNeedsContinuation(employee.value) : false,
);
const retryLabel = computed(() =>
  employee.value ? employeeFailureRetryActionLabel(employee.value) : 'Try again',
);
const actionsDisabled = computed(
  () => shell.composerAgentBusy || retrying.value,
);

function openComposerDraft(
  row: CompanyEmployeeRecord,
  kind: 'receipts',
): void {
  const { mode, draft } = employeeComposerOpenPayload(row, kind);
  if (mode) {
    requestIdeComposerMode(mode);
  }
  if (draft) {
    shell.openIdeComposerWithDraft(draft, { keepActivityView: true });
  } else {
    shell.openIdeComposer({ keepActivityView: true });
  }
  focusAgentDockComposerInput();
}

function handleReceipts(): void {
  const row = employee.value;
  if (!row) {
    return;
  }
  openComposerDraft(row, 'receipts');
}

function handleOpenTeam(): void {
  shell.revealTeamRosterForActiveEmployee();
}

async function handleRetry(): Promise<void> {
  const row = employee.value;
  if (!row || actionsDisabled.value) {
    return;
  }
  retrying.value = true;
  try {
    const result = await runEmployeeShiftRetry(shell, row, {
      keepActivityView: true,
      focusThread: true,
    });
    if (!result.ok) {
      shell.commandMutationError = result.reason;
    }
  } finally {
    retrying.value = false;
  }
}
</script>

<template>
  <div
    v-if="showBanner"
    class="agent-dock-notice agent-dock-notice--attention"
    :class="{ 'agent-dock-notice--interrupted': interruptedShift }"
    role="status"
    aria-live="polite"
    :aria-label="failureAriaLabel"
  >
    <span class="agent-dock-notice__rail" aria-hidden="true" />
    <div class="agent-dock-notice__body">
      <p
        class="agent-dock-notice__copy"
        :title="failureDetailTooltip"
      >
        {{ failureCopy }}
      </p>
      <div class="agent-dock-notice__actions">
        <button
          type="button"
          class="agent-dock-notice__primary"
          :disabled="actionsDisabled"
          :title="`${retryLabel} this teammate's last job`"
          @click="handleRetry"
        >
          {{ retrying ? 'Working…' : retryLabel }}
        </button>
        <button
          v-if="showReceiptsAction"
          type="button"
          class="agent-dock-notice__link"
          title="Opens Ask so they explain what happened without changing code"
          :disabled="actionsDisabled"
          @click="handleReceipts"
        >
          Explain
        </button>
        <button
          type="button"
          class="agent-dock-notice__link"
          @click="handleOpenTeam"
        >
          Open team
        </button>
      </div>
    </div>
  </div>
</template>

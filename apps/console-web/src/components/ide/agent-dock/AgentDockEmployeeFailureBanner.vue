<script setup lang="ts">
import { computed } from 'vue';

import type { CompanyEmployeeRecord } from '../../../contracts/canonical';
import { employeeComposerOpenPayload } from '../../../features/workspace-agents/company-roster-actions';
import {
  employeeDockReceiptRunId,
  employeeFailureBannerAriaLabel,
  employeeFailureBannerCopy,
  employeeFailureDetailTooltip,
} from '../../../features/workspace-agents/company-roster-view';
import { focusAgentDockComposerInput } from '../../../lib/agent-dock-composer-focus';
import { requestIdeComposerMode } from '../../../lib/ide-composer-restore-request';
import { shouldSurfaceIdeEmployeeFailure } from '../../../lib/ide-presence-profile';
import { useShellStore } from '../../../stores/shell';

const shell = useShellStore();

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
const actionsDisabled = computed(() => shell.composerAgentBusy);

function openComposerDraft(row: CompanyEmployeeRecord, kind: 'retry' | 'receipts'): void {
  const { mode, draft } = employeeComposerOpenPayload(row, kind);
  requestIdeComposerMode(mode);
  if (draft) {
    shell.openIdeComposerWithDraft(draft, { keepActivityView: true });
  } else {
    shell.openIdeComposer({ keepActivityView: true });
  }
  focusAgentDockComposerInput();
}

function handleRetry(): void {
  const row = employee.value;
  if (!row) {
    return;
  }
  openComposerDraft(row, 'retry');
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
</script>

<template>
  <div
    v-if="showBanner"
    class="agent-dock-composer__employee-failure-banner"
    role="status"
    aria-live="polite"
    :aria-label="failureAriaLabel"
  >
    <p
      class="agent-dock-composer__employee-failure-copy"
      :title="failureDetailTooltip"
    >
      {{ failureCopy }}
    </p>
    <div class="agent-dock-composer__employee-failure-actions">
      <button
        type="button"
        class="agent-dock-composer__employee-failure-btn agent-dock-composer__employee-failure-btn--retry"
        :disabled="actionsDisabled"
        @click="handleRetry"
      >
        Retry shift
      </button>
      <button
        v-if="showReceiptsAction"
        type="button"
        class="agent-dock-composer__employee-failure-btn agent-dock-composer__employee-failure-btn--receipts"
        :disabled="actionsDisabled"
        @click="handleReceipts"
      >
        View receipts
      </button>
      <button
        type="button"
        class="agent-dock-composer__employee-failure-btn agent-dock-composer__employee-failure-btn--team"
        @click="handleOpenTeam"
      >
        Open team
      </button>
    </div>
  </div>
</template>

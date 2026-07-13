<script setup lang="ts">
import { computed } from 'vue';

import { useWorkspaceCompany } from '../../features/workspace-agents/use-workspace-company';
import {
  companyHeadline,
  employeeMetaLine,
  employeeStatusLabel,
} from '../../features/workspace-agents/company-roster-view';
import { useShellStore } from '../../stores/shell';

const shell = useShellStore();
const currentWorkspaceId = computed(() => shell.currentWorkspace?.workspace_id ?? null);
const { company, employees, loadState, loadError } = useWorkspaceCompany(currentWorkspaceId);

const headline = computed(() =>
  companyHeadline(company.value?.company_name, company.value?.employee_count),
);
</script>

<template>
  <section
    v-if="currentWorkspaceId"
    class="company-roster"
    aria-label="Company employees"
  >
    <header class="company-roster__header">
      <p class="company-roster__eyebrow">Company team</p>
      <h3 class="company-roster__title">{{ headline }}</h3>
      <p class="company-roster__hint">
        Each workspace is a company. Employees cover watch, UI/UX, backend, and integrations.
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
        class="company-roster__row"
        :class="{
          'company-roster__row--primary': employee.primary,
          [`company-roster__row--${employee.role}`]: true,
        }"
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
      </li>
    </ul>
  </section>
</template>

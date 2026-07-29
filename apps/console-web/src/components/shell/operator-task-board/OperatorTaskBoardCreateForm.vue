<script setup lang="ts">
const goalDraft = defineModel<string>('goalDraft', { required: true });
const ownerRoleDraft = defineModel<string>('ownerRoleDraft', { required: true });
const acceptanceDraft = defineModel<string>('acceptanceDraft', { required: true });
const riskDraft = defineModel<string>('riskDraft', { required: true });
const attemptBudgetDraft = defineModel<number>('attemptBudgetDraft', { required: true });
const dependenciesDraft = defineModel<string>('dependenciesDraft', { required: true });
const createAsLeadPlan = defineModel<boolean>('createAsLeadPlan', { required: true });

defineProps<{
  roleOptions: Array<{ value: string; label: string }>;
  canCreate: boolean;
  workspaceTasksMutating: boolean;
  leadPlansMutating: boolean;
}>();

const emit = defineEmits<{
  submit: [];
}>();
</script>

<template>
  <form class="operator-task-board__form" data-orb-field @submit.prevent="emit('submit')">
    <label class="operator-task-board__field">
      <span class="operator-task-board__field-label">Goal</span>
      <input
        v-model="goalDraft"
        class="operator-task-board__input"
        type="text"
        maxlength="240"
        placeholder="What should this specialist finish?"
        :disabled="workspaceTasksMutating || leadPlansMutating"
      />
    </label>
    <label class="operator-task-board__field operator-task-board__field--role">
      <span class="operator-task-board__field-label">Role</span>
      <select
        v-model="ownerRoleDraft"
        class="operator-task-board__select"
        :disabled="createAsLeadPlan || workspaceTasksMutating"
      >
        <option v-for="role in roleOptions" :key="role.value" :value="role.value">
          {{ role.label }}
        </option>
      </select>
    </label>
    <label class="operator-task-board__field">
      <span class="operator-task-board__field-label">Risk</span>
      <select
        v-model="riskDraft"
        class="operator-task-board__select"
        :disabled="createAsLeadPlan || workspaceTasksMutating"
      >
        <option value="low">Low</option>
        <option value="normal">Normal</option>
        <option value="high">High</option>
      </select>
    </label>
    <label class="operator-task-board__field">
      <span class="operator-task-board__field-label">Attempts</span>
      <input
        v-model.number="attemptBudgetDraft"
        class="operator-task-board__input"
        type="number"
        min="1"
        max="32"
        :disabled="createAsLeadPlan || workspaceTasksMutating"
      />
    </label>
    <label class="operator-task-board__field operator-task-board__field--wide">
      <span class="operator-task-board__field-label">Done when</span>
      <input
        v-model="acceptanceDraft"
        class="operator-task-board__input"
        type="text"
        maxlength="240"
        placeholder="Optional acceptance criteria"
        :disabled="createAsLeadPlan || workspaceTasksMutating"
      />
    </label>
    <label class="operator-task-board__field operator-task-board__field--wide">
      <span class="operator-task-board__field-label">Dependencies</span>
      <input
        v-model="dependenciesDraft"
        class="operator-task-board__input"
        type="text"
        maxlength="320"
        placeholder="Optional task ids, comma-separated"
        :disabled="createAsLeadPlan || workspaceTasksMutating"
      />
    </label>
    <label class="operator-task-board__field operator-task-board__field--wide operator-task-board__check">
      <input v-model="createAsLeadPlan" type="checkbox" />
      <span>Create as Lead plan fan-out (multi-role)</span>
    </label>
    <button type="submit" class="operator-task-board__submit" :disabled="!canCreate">
      {{ createAsLeadPlan ? 'Fan out Lead plan' : 'Create task' }}
    </button>
  </form>
</template>

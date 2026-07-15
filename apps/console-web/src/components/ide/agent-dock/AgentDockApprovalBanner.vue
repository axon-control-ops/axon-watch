<script setup lang="ts">
defineProps<{
  show: boolean;
  canApprove: boolean;
  rejectPending: boolean;
}>();

const emit = defineEmits<{
  approve: [];
  reject: [];
}>();
</script>

<template>
  <div
    v-if="show"
    class="agent-dock-composer__approval-banner"
    role="status"
  >
    <p class="agent-dock-composer__approval-copy">
      Full Access is waiting for approval before tools can edit files or run commands.
    </p>
    <div class="agent-dock-composer__approval-actions">
      <button
        type="button"
        class="agent-dock-composer__approval-btn agent-dock-composer__approval-btn--approve"
        :disabled="!canApprove"
        @click="emit('approve')"
      >
        Approve
      </button>
      <button
        type="button"
        class="agent-dock-composer__approval-btn agent-dock-composer__approval-btn--reject"
        :disabled="rejectPending"
        @click="emit('reject')"
      >
        Reject
      </button>
    </div>
  </div>
</template>

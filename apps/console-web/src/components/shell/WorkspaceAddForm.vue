<script setup lang="ts">
import { computed, ref } from 'vue';

import { useShellStore } from '../../stores/shell';

const emit = defineEmits<{
  registered: [workspaceId: string];
  cancel: [];
}>();

const shell = useShellStore();
const workspaceId = ref('');
const projectRoot = ref('');
const displayName = ref('');
const busy = ref(false);
const error = ref('');

const canSubmit = computed(
  () =>
    Boolean(workspaceId.value.trim()) &&
    Boolean(projectRoot.value.trim()) &&
    !busy.value,
);

async function submit(): Promise<void> {
  if (!canSubmit.value) {
    return;
  }
  busy.value = true;
  error.value = '';
  try {
    const workspace = await shell.registerWorkspace({
      workspaceId: workspaceId.value.trim(),
      projectRoot: projectRoot.value.trim(),
      displayName: displayName.value.trim() || undefined,
    });
    shell.setCurrentWorkspace(workspace.workspace_id);
    emit('registered', workspace.workspace_id);
  } catch (exc) {
    const message = exc instanceof Error ? exc.message : 'Failed to add workspace';
    error.value = message;
  } finally {
    busy.value = false;
  }
}
</script>

<template>
  <form class="workspace-add-form" @submit.prevent="submit">
    <p class="workspace-add-form__title">Add workspace</p>
    <label class="workspace-add-form__field">
      <span>Workspace id</span>
      <input
        v-model="workspaceId"
        type="text"
        name="workspace_id"
        autocomplete="off"
        placeholder="workspace_my_project"
        required
      />
    </label>
    <label class="workspace-add-form__field">
      <span>Project root</span>
      <input
        v-model="projectRoot"
        type="text"
        name="project_root"
        autocomplete="off"
        placeholder="/run/media/vaxon/axon-data/path/to/repo"
        required
      />
    </label>
    <label class="workspace-add-form__field">
      <span>Display name (optional)</span>
      <input
        v-model="displayName"
        type="text"
        name="display_name"
        autocomplete="off"
        placeholder="My project"
      />
    </label>
    <p v-if="error" class="workspace-add-form__error" role="alert">{{ error }}</p>
    <div class="workspace-add-form__actions">
      <button type="button" class="workspace-add-form__button" @click="emit('cancel')">
        Cancel
      </button>
      <button
        type="submit"
        class="workspace-add-form__button workspace-add-form__button--primary"
        :disabled="!canSubmit"
      >
        {{ busy ? 'Adding…' : 'Add' }}
      </button>
    </div>
  </form>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';

import { axonDebugSessionLog } from '../../lib/axon-debug-session-log';
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

onMounted(() => {
  // #region agent log
  axonDebugSessionLog({
    hypothesisId: 'H1',
    location: 'WorkspaceAddForm.vue:onMounted',
    message: 'Add workspace form opened',
    data: {
      requiresWorkspaceId: true,
      requiresProjectRoot: true,
      hasBrowseControl: false,
      hasNativeDirectoryPickerApi:
        typeof (window as Window & { showDirectoryPicker?: unknown }).showDirectoryPicker ===
        'function',
      fieldNames: ['workspace_id', 'project_root', 'display_name'],
    },
  });
  // #endregion
});

function onProjectRootInput(): void {
  // #region agent log
  axonDebugSessionLog({
    hypothesisId: 'H2',
    location: 'WorkspaceAddForm.vue:onProjectRootInput',
    message: 'Project root typed manually (no folder picker invoked)',
    data: {
      projectRootLength: projectRoot.value.trim().length,
      looksAbsolute: projectRoot.value.trim().startsWith('/'),
      workspaceIdEmpty: !workspaceId.value.trim(),
      displayNameEmpty: !displayName.value.trim(),
    },
  });
  // #endregion
}

async function submit(): Promise<void> {
  // #region agent log
  axonDebugSessionLog({
    hypothesisId: 'H1',
    location: 'WorkspaceAddForm.vue:submit',
    message: 'Add workspace submit attempted',
    data: {
      canSubmit: canSubmit.value,
      workspaceIdLength: workspaceId.value.trim().length,
      projectRootLength: projectRoot.value.trim().length,
      hasDisplayName: Boolean(displayName.value.trim()),
      workspaceIdPrefixOk: workspaceId.value.trim().startsWith('workspace_'),
    },
  });
  // #endregion
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
    // #region agent log
    axonDebugSessionLog({
      hypothesisId: 'H4',
      location: 'WorkspaceAddForm.vue:submit:success',
      message: 'Workspace registered successfully',
      data: { registeredId: workspace.workspace_id },
      workspaceId: workspace.workspace_id,
    });
    // #endregion
    shell.setCurrentWorkspace(workspace.workspace_id);
    emit('registered', workspace.workspace_id);
  } catch (exc) {
    const message = exc instanceof Error ? exc.message : 'Failed to add workspace';
    // #region agent log
    axonDebugSessionLog({
      hypothesisId: 'H4',
      location: 'WorkspaceAddForm.vue:submit:error',
      message: 'Workspace register failed',
      data: { error: message },
    });
    // #endregion
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
        placeholder="/home/edp/path/to/repo"
        required
        @input="onProjectRootInput"
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

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue';

import {
  fetchWorkspaceProjectRootSuggestions,
  type WorkspaceProjectRootSuggestion,
} from '../../api/workspace-api';
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

// Suggests a project_root from sibling directories of already-registered
// workspaces, ranked against the workspace id as the operator types — the
// operator can still always override by typing their own path directly.
const suggestions = ref<WorkspaceProjectRootSuggestion[]>([]);
const suggestionsLoading = ref(false);
const projectRootTouchedByOperator = ref(false);
let suggestionRequestId = 0;
let suggestionDebounce: ReturnType<typeof setTimeout> | null = null;

async function loadSuggestions(query: string): Promise<void> {
  const requestId = ++suggestionRequestId;
  suggestionsLoading.value = true;
  try {
    const snapshot = await fetchWorkspaceProjectRootSuggestions(query);
    if (requestId !== suggestionRequestId) {
      return;
    }
    suggestions.value = snapshot.items;
  } catch {
    if (requestId === suggestionRequestId) {
      suggestions.value = [];
    }
  } finally {
    if (requestId === suggestionRequestId) {
      suggestionsLoading.value = false;
    }
  }
}

function scheduleSuggestions(query: string): void {
  if (suggestionDebounce) {
    clearTimeout(suggestionDebounce);
  }
  suggestionDebounce = setTimeout(() => {
    void loadSuggestions(query);
  }, 220);
}

function applySuggestion(suggestion: WorkspaceProjectRootSuggestion): void {
  projectRoot.value = suggestion.project_root;
  projectRootTouchedByOperator.value = true;
  if (!displayName.value.trim()) {
    displayName.value = suggestion.label;
  }
  suggestions.value = [];
}

watch(workspaceId, (value) => {
  scheduleSuggestions(value);
});

onMounted(() => {
  scheduleSuggestions('');
});

onUnmounted(() => {
  if (suggestionDebounce) {
    clearTimeout(suggestionDebounce);
  }
});

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
        @input="projectRootTouchedByOperator = true"
      />
    </label>
    <div
      v-if="!projectRootTouchedByOperator && (suggestions.length || suggestionsLoading)"
      class="workspace-add-form__suggestions"
    >
      <p class="workspace-add-form__suggestions-label">
        {{ suggestionsLoading ? 'Looking for a matching project…' : 'Suggested project root' }}
      </p>
      <button
        v-for="suggestion in suggestions"
        :key="suggestion.project_root"
        type="button"
        class="workspace-add-form__suggestion"
        :title="suggestion.project_root"
        @click="applySuggestion(suggestion)"
      >
        <span class="workspace-add-form__suggestion-label">{{ suggestion.label }}</span>
        <span class="workspace-add-form__suggestion-parent">{{ suggestion.parent }}</span>
      </button>
    </div>
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

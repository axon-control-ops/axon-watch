<script setup lang="ts">
import { computed, ref, watch } from 'vue';

import {
  captureOperatorResearch,
  createOperatorMemory,
  fetchOperatorEvidence,
  fetchOperatorMemories,
  type OperatorEvidenceRecord,
  type OperatorMemoryRecord,
} from '../../api/operator-api';

const props = defineProps<{
  nodeId: string | null;
  fallbackTitle: string;
  fallbackBody: string;
  fallbackHint: string;
}>();

const emit = defineEmits<{
  openWorkspace: [workspaceId: string];
  openSignal: [signalId: string];
}>();

const loading = ref(false);
const error = ref<string | null>(null);
const evidence = ref<OperatorEvidenceRecord | null>(null);
const memories = ref<OperatorMemoryRecord[]>([]);
const memoryTitle = ref('');
const memoryContent = ref('');
const researchQuery = ref('');
const statusLine = ref('');

const workspaceId = computed(() => {
  const source = evidence.value?.sources.find((item) => item.workspace_id?.trim());
  return source?.workspace_id?.trim() ?? '';
});

const shownTitle = computed(() => evidence.value?.title ?? props.fallbackTitle);
const shownBody = computed(() => evidence.value?.summary ?? props.fallbackBody);
const shownHint = computed(() => props.fallbackHint);

async function loadPanel(nodeId: string | null): Promise<void> {
  evidence.value = null;
  memories.value = [];
  error.value = null;
  statusLine.value = '';
  if (!nodeId) {
    return;
  }
  loading.value = true;
  try {
    evidence.value = await fetchOperatorEvidence(nodeId);
    researchQuery.value = evidence.value.title;
    const scopedWorkspaceId =
      evidence.value.sources.find((item) => item.workspace_id?.trim())?.workspace_id ?? '';
    const response = await fetchOperatorMemories({
      workspaceId: scopedWorkspaceId,
      limit: 6,
    });
    memories.value = response.items;
  } catch (nextError) {
    error.value = nextError instanceof Error ? nextError.message : 'evidence request failed';
  } finally {
    loading.value = false;
  }
}

async function saveMemory(): Promise<void> {
  if (!evidence.value || !memoryTitle.value.trim() || !memoryContent.value.trim()) {
    return;
  }
  const response = await createOperatorMemory({
    workspace_id: workspaceId.value,
    scope: workspaceId.value ? 'workspace' : 'personal',
    kind: 'note',
    title: memoryTitle.value.trim(),
    content: memoryContent.value.trim(),
    source_refs: evidence.value.sources,
  });
  memories.value = [response.item, ...memories.value].slice(0, 6);
  memoryTitle.value = '';
  memoryContent.value = '';
  statusLine.value = 'Memory saved with citations.';
}

async function captureResearch(): Promise<void> {
  if (!researchQuery.value.trim()) {
    return;
  }
  const response = await captureOperatorResearch({
    workspace_id: workspaceId.value,
    title: researchQuery.value.trim(),
    query: researchQuery.value.trim(),
    source_refs: evidence.value?.sources ?? [],
  });
  memories.value = [response.memory, ...memories.value].slice(0, 6);
  statusLine.value = 'Research captured and stored as cited memory.';
}

function triggerAction(action: OperatorEvidenceRecord['actions'][number]): void {
  if (action.target === 'workspace' && action.workspace_id) {
    emit('openWorkspace', action.workspace_id);
  }
  if (action.target === 'signal' && action.signal_id) {
    emit('openSignal', action.signal_id);
  }
}

watch(
  () => props.nodeId,
  (nodeId) => {
    void loadPanel(nodeId);
  },
  { immediate: true },
);
</script>

<template>
  <aside class="brain-galaxy-stage__hud brain-galaxy-stage__hud--inspector">
    <p class="brain-galaxy-stage__inspector-title">{{ shownTitle }}</p>
    <p class="brain-galaxy-stage__inspector-body">{{ shownBody }}</p>
    <p class="brain-galaxy-stage__inspector-hint">{{ shownHint }}</p>

    <p v-if="loading" class="region-copy">Loading evidence…</p>
    <p v-else-if="error" class="region-copy region-copy--degraded">{{ error }}</p>

    <template v-else-if="evidence">
      <div v-if="evidence.facts.length" class="briefing-panel__section">
        <p class="briefing-panel__section-label">Evidence facts</p>
        <ul class="briefing-panel__list">
          <li v-for="fact in evidence.facts" :key="fact.label" class="briefing-panel__item">
            <span class="briefing-panel__item-title">{{ fact.label }}</span>
            <span class="region-copy">{{ fact.value }}</span>
          </li>
        </ul>
      </div>

      <div v-for="section in evidence.sections" :key="section.title" class="briefing-panel__section">
        <p class="briefing-panel__section-label">{{ section.title }}</p>
        <ul class="briefing-panel__list">
          <li v-for="item in section.items" :key="`${section.title}:${item.title}`" class="briefing-panel__item">
            <span class="briefing-panel__item-title">{{ item.title }}</span>
            <span class="region-copy">{{ item.detail }}</span>
            <span v-if="item.source_ref" class="briefing-panel__kind">
              {{ item.source_ref.label }}
            </span>
          </li>
        </ul>
      </div>

      <div v-if="evidence.actions.length" class="briefing-panel__section">
        <p class="briefing-panel__section-label">Panel actions</p>
        <div class="briefing-panel__chips">
          <button
            v-for="action in evidence.actions"
            :key="action.label"
            type="button"
            class="briefing-panel__chip"
            @click="triggerAction(action)"
          >
            {{ action.label }}
          </button>
        </div>
      </div>

      <div class="briefing-panel__section">
        <p class="briefing-panel__section-label">Remember this</p>
        <input v-model="memoryTitle" class="kairo-conversation-bar__input" type="text" placeholder="Short note title" />
        <textarea
          v-model="memoryContent"
          class="briefing-panel__memory-input"
          rows="3"
          placeholder="Confirmed note, tied to the evidence above…"
        />
        <button type="button" class="briefing-panel__cta" @click="saveMemory">Save cited memory</button>
      </div>

      <div class="briefing-panel__section">
        <p class="briefing-panel__section-label">Research capture</p>
        <input
          v-model="researchQuery"
          class="kairo-conversation-bar__input"
          type="text"
          placeholder="Question to research and capture"
        />
        <button type="button" class="briefing-panel__cta" @click="captureResearch">
          Capture research
        </button>
      </div>

      <div v-if="memories.length" class="briefing-panel__section">
        <p class="briefing-panel__section-label">Recent memories</p>
        <ul class="briefing-panel__list">
          <li v-for="memory in memories" :key="memory.memory_id" class="briefing-panel__item">
            <span class="briefing-panel__item-title">{{ memory.title }}</span>
            <span class="region-copy">{{ memory.content }}</span>
            <span class="briefing-panel__kind">{{ memory.kind }}</span>
          </li>
        </ul>
      </div>

      <p v-if="statusLine" class="region-copy">{{ statusLine }}</p>
    </template>
  </aside>
</template>


<script setup lang="ts">
import { computed, ref, watch } from 'vue';

import {
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
  dismiss: [];
  openWorkspace: [workspaceId: string];
  openSignal: [signalId: string];
  handoffSignal: [
    signal: {
      signal_id: string;
      workspace_id?: string | null;
      title: string;
      summary?: string | null;
      meta?: Record<string, unknown> | null;
    },
  ];
}>();

const loading = ref(false);
const error = ref<string | null>(null);
const evidence = ref<OperatorEvidenceRecord | null>(null);
const memories = ref<OperatorMemoryRecord[]>([]);
const memoryExpanded = ref(false);
const memoryTitle = ref('');
const memoryContent = ref('');
const statusLine = ref('');

const workspaceId = computed(() => {
  const source = evidence.value?.sources.find((item) => item.workspace_id?.trim());
  return source?.workspace_id?.trim() ?? '';
});

const shownTitle = computed(() => evidence.value?.title ?? props.fallbackTitle);
const shownBody = computed(() => evidence.value?.summary ?? props.fallbackBody);
const shownHint = computed(() => {
  if (evidence.value && !loading.value && !error.value) {
    return '';
  }
  return props.fallbackHint;
});
const kindLabel = computed(() => {
  const kind = evidence.value?.kind ?? 'node';
  if (kind === 'core') {
    return 'System Node';
  }
  return kind.charAt(0).toUpperCase() + kind.slice(1);
});

const EVIDENCE_ICONS = ['doc', 'link', 'db', 'pulse', 'shield', 'mail'] as const;

const evidenceRows = computed(() => {
  const rows: Array<{
    id: string;
    title: string;
    detail: string;
    source: string;
    ago: string;
    icon: (typeof EVIDENCE_ICONS)[number];
  }> = [];
  const sections = evidence.value?.sections ?? [];
  if (sections.length) {
    for (const section of sections) {
      for (const item of section.items) {
        rows.push({
          id: `section:${section.title}:${item.title}`,
          title: item.title,
          detail: item.detail,
          source: item.source_ref?.label || section.title,
          ago: '',
          icon: EVIDENCE_ICONS[rows.length % EVIDENCE_ICONS.length] ?? 'doc',
        });
      }
    }
  } else {
    for (const fact of evidence.value?.facts ?? []) {
      rows.push({
        id: `fact:${fact.label}`,
        title: fact.label,
        detail: fact.value,
        source: 'Evidence',
        ago: '',
        icon: EVIDENCE_ICONS[rows.length % EVIDENCE_ICONS.length] ?? 'doc',
      });
    }
  }
  return rows.slice(0, 8);
});

const tags = computed(() => {
  const kind = evidence.value?.kind;
  const next = [kind, workspaceId.value ? 'workspace' : null].filter(Boolean) as string[];
  if (kind === 'core') {
    return ['core', 'system', 'high_value', 'trusted'];
  }
  if (kind === 'signal') {
    next.push('attention');
  }
  return next.slice(0, 4);
});

const primaryAction = computed(() => evidence.value?.actions[0] ?? null);

async function loadPanel(nodeId: string | null): Promise<void> {
  evidence.value = null;
  memories.value = [];
  error.value = null;
  statusLine.value = '';
  memoryExpanded.value = false;
  if (!nodeId) {
    return;
  }
  loading.value = true;
  try {
    evidence.value = await fetchOperatorEvidence(nodeId);
    const scopedWorkspaceId =
      evidence.value.sources.find((item) => item.workspace_id?.trim())?.workspace_id ?? '';
    const response = await fetchOperatorMemories({
      workspaceId: scopedWorkspaceId,
      limit: 4,
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
  memories.value = [response.item, ...memories.value].slice(0, 4);
  memoryTitle.value = '';
  memoryContent.value = '';
  statusLine.value = 'Memory saved.';
}

function factValue(label: string): string {
  const facts = evidence.value?.facts ?? [];
  return facts.find((fact) => fact.label === label)?.value?.trim() ?? '';
}

function evidenceHandoffMeta(): Record<string, unknown> | null {
  const family = factValue('Family');
  if (family !== 'email_triage') {
    return null;
  }
  return {
    signal_family: family,
    sender: factValue('Sender'),
    subject: factValue('Subject'),
    recommended_action: factValue('Recommended action'),
    recommended_detail: evidence.value?.summary ?? '',
  };
}

function triggerAction(action: OperatorEvidenceRecord['actions'][number]): void {
  if (action.target === 'workspace' && action.workspace_id) {
    emit('openWorkspace', action.workspace_id);
  }
  if (action.target === 'signal' && action.signal_id) {
    emit('openSignal', action.signal_id);
  }
  if (action.target === 'handoff' && action.signal_id && evidence.value) {
    emit('handoffSignal', {
      signal_id: action.signal_id,
      workspace_id: action.workspace_id ?? workspaceId.value,
      title: evidence.value.title,
      summary: evidence.value.summary,
      meta: evidenceHandoffMeta(),
    });
  }
}

async function copyNodeId(): Promise<void> {
  if (!props.nodeId || !navigator.clipboard) {
    return;
  }
  await navigator.clipboard.writeText(props.nodeId);
  statusLine.value = 'ID copied.';
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
  <aside class="galaxy-inspector" role="dialog" aria-label="Node evidence inspector">
    <header class="galaxy-inspector__header">
      <p class="galaxy-inspector__eyebrow">{{ shownTitle }}</p>
      <button
        type="button"
        class="galaxy-inspector__close"
        aria-label="Dismiss evidence panel"
        title="Dismiss (Esc)"
        @click="emit('dismiss')"
      >
        ×
      </button>
    </header>

    <div class="galaxy-inspector__entity">
      <span class="galaxy-inspector__glyph" aria-hidden="true">⬡</span>
      <div class="galaxy-inspector__entity-copy">
        <p class="galaxy-inspector__entity-label">Entity</p>
        <strong>{{ shownTitle }}</strong>
        <span>Type: {{ kindLabel }}</span>
        <button
          v-if="nodeId"
          type="button"
          class="galaxy-inspector__id"
          title="Copy node ID"
          @click="copyNodeId"
        >
          ID: {{ nodeId }}
        </button>
      </div>
    </div>

    <p class="galaxy-inspector__summary">{{ shownBody }}</p>
    <p v-if="shownHint" class="galaxy-inspector__hint">{{ shownHint }}</p>

    <p v-if="loading" class="galaxy-inspector__status">Loading evidence…</p>
    <p v-else-if="error" class="galaxy-inspector__status galaxy-inspector__status--error">
      {{ error }}
    </p>

    <template v-else>
      <section v-if="evidenceRows.length" class="galaxy-inspector__section">
        <p class="galaxy-inspector__section-label">
          Evidence
          <span>{{ evidenceRows.length }}</span>
        </p>
        <ul class="galaxy-inspector__evidence">
          <li v-for="row in evidenceRows" :key="row.id">
            <span
              class="galaxy-inspector__evidence-icon"
              :class="`galaxy-inspector__evidence-icon--${row.icon}`"
              aria-hidden="true"
            />
            <div>
              <strong>{{ row.title }}</strong>
              <p>{{ row.detail }}</p>
              <span>Source: {{ row.source }}</span>
            </div>
          </li>
        </ul>
      </section>

      <div v-if="tags.length" class="galaxy-inspector__tags-wrap">
        <p class="galaxy-inspector__section-label">Tags</p>
        <div class="galaxy-inspector__tags">
          <span v-for="tag in tags" :key="tag">{{ tag }}</span>
        </div>
      </div>

      <button
        v-if="primaryAction"
        type="button"
        class="galaxy-inspector__cta"
        @click="triggerAction(primaryAction)"
      >
        <span aria-hidden="true">◎</span>
        {{ primaryAction.label }}
      </button>

      <button
        v-for="action in (evidence?.actions ?? []).slice(1)"
        :key="action.label"
        type="button"
        class="galaxy-inspector__cta galaxy-inspector__cta--ghost"
        @click="triggerAction(action)"
      >
        {{ action.label }}
      </button>

      <details class="galaxy-inspector__more" :open="memoryExpanded">
        <summary @click.prevent="memoryExpanded = !memoryExpanded">Remember / notes</summary>
        <div class="galaxy-inspector__more-body">
          <input
            v-model="memoryTitle"
            class="galaxy-inspector__input"
            type="text"
            placeholder="Short note title"
          />
          <textarea
            v-model="memoryContent"
            class="galaxy-inspector__textarea"
            rows="3"
            placeholder="Confirmed note tied to this evidence…"
          />
          <button type="button" class="galaxy-inspector__cta galaxy-inspector__cta--ghost" @click="saveMemory">
            Save cited memory
          </button>
          <ul v-if="memories.length" class="galaxy-inspector__evidence">
            <li v-for="memory in memories" :key="memory.memory_id">
              <span class="galaxy-inspector__evidence-icon galaxy-inspector__evidence-icon--doc" aria-hidden="true" />
              <div>
                <strong>{{ memory.title }}</strong>
                <p>{{ memory.content }}</p>
                <span>{{ memory.kind }}</span>
              </div>
            </li>
          </ul>
          <p v-if="statusLine" class="galaxy-inspector__status">{{ statusLine }}</p>
        </div>
      </details>
    </template>
  </aside>
</template>

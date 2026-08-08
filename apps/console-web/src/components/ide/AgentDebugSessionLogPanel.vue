<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue';

import {
  fetchDebugSessionLog,
  type DebugSessionLogEntry,
} from '../../api/debug-session-api';
import {
  isDebugLogPinnedToBottom,
  scrollDebugLogToBottom,
} from '../../lib/debug-session-log-scroll';
import { formatDebugSessionLogEntry } from '../../lib/debug-session-log-view';

const props = defineProps<{
  workspaceId?: string | null;
  /** Compact layout for the sticky composer banner. */
  compact?: boolean;
}>();

const entries = ref<DebugSessionLogEntry[]>([]);
const stale = ref(false);
const loadError = ref<string | null>(null);
const expanded = ref(true);
const lastSeenCount = ref(0);
const listEl = ref<HTMLElement | null>(null);
/** Cursor-like: stay glued to newest unless the operator scrolls up. */
const pinnedToBottom = ref(true);
let pollTimer: ReturnType<typeof setInterval> | null = null;

/** Chronological — oldest top, newest bottom (terminal / Cursor style). */
const displayRows = computed(() =>
  entries.value.map((entry, index) => ({
    key: `${entry.timestamp ?? ''}:${entry.hypothesisId ?? ''}:${entry.message ?? ''}:${index}`,
    ...formatDebugSessionLogEntry(entry),
  })),
);

function onListScroll(): void {
  const el = listEl.value;
  if (!el) {
    return;
  }
  pinnedToBottom.value = isDebugLogPinnedToBottom(el);
}

async function stickToBottomIfPinned(): Promise<void> {
  if (!pinnedToBottom.value) {
    return;
  }
  await nextTick();
  const el = listEl.value;
  if (!el) {
    return;
  }
  scrollDebugLogToBottom(el);
  // Layout can settle one frame later when many rows mount at once.
  requestAnimationFrame(() => {
    const node = listEl.value;
    if (!node || !pinnedToBottom.value) {
      return;
    }
    scrollDebugLogToBottom(node);
  });
}

async function refreshLogs(): Promise<void> {
  try {
    const payload = await fetchDebugSessionLog({
      workspaceId: props.workspaceId,
      limit: 80,
    });
    loadError.value = null;
    const prevCount = lastSeenCount.value;
    if (payload.entries.length > 0) {
      entries.value = payload.entries;
      stale.value = false;
      lastSeenCount.value = payload.entries.length;
      if (payload.entries.length !== prevCount) {
        await stickToBottomIfPinned();
      }
    } else if (entries.value.length > 0) {
      stale.value = true;
    } else {
      entries.value = [];
      stale.value = false;
      lastSeenCount.value = 0;
    }
  } catch (error) {
    loadError.value = error instanceof Error ? error.message : 'Failed to load debug logs';
  }
}

function startPolling(): void {
  stopPolling();
  pinnedToBottom.value = true;
  void refreshLogs();
  pollTimer = setInterval(() => {
    void refreshLogs();
  }, 750);
}

function stopPolling(): void {
  if (pollTimer) {
    clearInterval(pollTimer);
    pollTimer = null;
  }
}

onMounted(() => {
  startPolling();
});

onUnmounted(() => {
  stopPolling();
});

watch(
  () => props.workspaceId,
  () => {
    startPolling();
  },
);

watch(expanded, (isOpen) => {
  if (isOpen) {
    pinnedToBottom.value = true;
    void stickToBottomIfPinned();
  }
});
</script>

<template>
  <div
    class="agent-debug-session-log-panel"
    :class="{ 'agent-debug-session-log-panel--compact': compact }"
  >
    <button
      type="button"
      class="agent-debug-session-log-panel__toggle"
      :aria-expanded="expanded"
      @click="expanded = !expanded"
    >
      Runtime logs
      <span class="agent-debug-session-log-panel__count">{{ entries.length }}</span>
      <span v-if="stale" class="agent-debug-session-log-panel__stale">last capture</span>
    </button>
    <div
      v-if="expanded"
      ref="listEl"
      class="agent-debug-session-log-panel__body"
      @scroll="onListScroll"
    >
      <p v-if="loadError" class="agent-debug-session-log-panel__empty">{{ loadError }}</p>
      <p v-else-if="!entries.length" class="agent-debug-session-log-panel__empty">
        Waiting for live evidence…
      </p>
      <ul v-else class="agent-debug-session-log-panel__list">
        <li v-for="row in displayRows" :key="row.key" class="agent-debug-session-log-panel__row">
          <span class="agent-debug-session-log-panel__hyp">{{ row.hypothesisLabel }}</span>
          <div class="agent-debug-session-log-panel__content">
            <p class="agent-debug-session-log-panel__title">{{ row.title }}</p>
            <p v-if="row.details.length" class="agent-debug-session-log-panel__details">
              {{ row.details.join(' · ') }}
            </p>
            <p v-if="row.locationShort" class="agent-debug-session-log-panel__loc">
              {{ row.locationShort }}
            </p>
          </div>
        </li>
      </ul>
    </div>
  </div>
</template>

<style scoped>
.agent-debug-session-log-panel {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
  min-width: 0;
}

.agent-debug-session-log-panel__toggle {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  align-self: flex-start;
  padding: 0;
  border: 0;
  background: transparent;
  color: rgba(196, 181, 253, 0.96);
  font: inherit;
  font-size: 0.62rem;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  cursor: pointer;
}

.agent-debug-session-log-panel__count {
  min-width: 1.1rem;
  padding: 0.05rem 0.28rem;
  border-radius: 999px;
  background: rgba(167, 139, 250, 0.22);
  text-align: center;
}

.agent-debug-session-log-panel__stale {
  text-transform: none;
  letter-spacing: 0;
  color: rgba(251, 191, 36, 0.92);
}

.agent-debug-session-log-panel__body {
  max-height: 12rem;
  overflow: auto;
  border-radius: 0.28rem;
  background: rgba(8, 6, 18, 0.72);
  padding: 0.35rem 0.45rem;
  scroll-behavior: auto;
}

.agent-debug-session-log-panel--compact .agent-debug-session-log-panel__body {
  max-height: 10rem;
}

.agent-debug-session-log-panel__empty {
  margin: 0;
  font-size: 0.62rem;
  color: rgba(200, 190, 230, 0.78);
}

.agent-debug-session-log-panel__list {
  margin: 0;
  padding: 0;
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

.agent-debug-session-log-panel__row {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: 0.4rem;
  align-items: start;
}

.agent-debug-session-log-panel__hyp {
  flex-shrink: 0;
  margin-top: 0.05rem;
  padding: 0.06rem 0.28rem;
  border-radius: 0.2rem;
  border: 1px solid rgba(167, 139, 250, 0.42);
  background: rgba(91, 33, 182, 0.35);
  color: rgba(237, 233, 254, 0.96);
  font-size: 0.55rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  line-height: 1.2;
}

.agent-debug-session-log-panel__content {
  min-width: 0;
}

.agent-debug-session-log-panel__title {
  margin: 0;
  font-size: 0.68rem;
  font-weight: 600;
  line-height: 1.3;
  color: rgba(245, 243, 255, 0.96);
}

.agent-debug-session-log-panel__details {
  margin: 0.12rem 0 0;
  font-size: 0.6rem;
  line-height: 1.35;
  color: rgba(216, 210, 240, 0.88);
  word-break: break-word;
}

.agent-debug-session-log-panel__loc {
  margin: 0.1rem 0 0;
  font-size: 0.52rem;
  letter-spacing: 0.02em;
  color: rgba(167, 139, 250, 0.72);
}
</style>

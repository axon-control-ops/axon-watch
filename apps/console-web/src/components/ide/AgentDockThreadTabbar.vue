<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue';

import WorkbenchIcon from '../WorkbenchIcon.vue';
import WorkspaceIcon from '../WorkspaceIcon.vue';
import {
  buildIdeThreadBusySet,
  buildIdeThreadFailureDetailTooltipMap,
  buildIdeThreadFailureHintMap,
} from '../../features/workspace-agents/active-ide-employee';
import { employeeIsActivelyBusy } from '../../features/workspace-agents/company-roster-view';
import {
  ideThreadMenuLabel,
  ideThreadMenuMeta,
  sortIdeThreadsNewestFirst,
} from '../../lib/ide-thread-picker-view';
import { ideThreadTabTitle } from '../../lib/ide-thread-tabs-view';
import { useShellStore } from '../../stores/shell';

const shell = useShellStore();
const historyOpen = ref(false);
const menuRef = ref<HTMLElement | null>(null);
const tabsRef = ref<HTMLElement | null>(null);
const canScrollLeft = ref(false);
const canScrollRight = ref(false);

const openTabs = computed(() => shell.openIdeThreadTabsForCurrentWorkspace);
const allThreads = computed(() =>
  sortIdeThreadsNewestFirst(shell.ideThreadsForCurrentWorkspace),
);
const liveBusyEmployeeIds = computed(() => {
  const ids = new Set<string>();
  const employees = shell.companyEmployeesForCurrentWorkspace;
  for (const row of employees) {
    if (employeeIsActivelyBusy(row)) {
      ids.add(row.employee_id);
    }
  }
  if (shell.agentStreamActive) {
    const threadEmployeeId = shell.activeIdeThread?.employee_id?.trim();
    const recordEmployeeId = shell.activeIdeEmployeeRecord?.employee_id?.trim();
    const primaryId =
      employees.find((row) => row.primary)?.employee_id?.trim() ||
      employees.find((row) => row.role === 'lead')?.employee_id?.trim() ||
      null;
    const streamOwnerId = threadEmployeeId || recordEmployeeId || primaryId;
    if (streamOwnerId) {
      ids.add(streamOwnerId);
    }
  }
  return [...ids];
});
const threadFailureHintById = computed(() =>
  buildIdeThreadFailureHintMap({
    threads: allThreads.value,
    employees: shell.companyEmployeesForCurrentWorkspace,
  }),
);
const threadFailureDetailById = computed(() =>
  buildIdeThreadFailureDetailTooltipMap({
    threads: allThreads.value,
    employees: shell.companyEmployeesForCurrentWorkspace,
  }),
);
const busyThreadIds = computed(() =>
  buildIdeThreadBusySet({
    threads: openTabs.value,
    employees: shell.companyEmployeesForCurrentWorkspace,
    liveBusyEmployeeIds: liveBusyEmployeeIds.value,
  }),
);

watch(
  busyThreadIds,
  (ids) => {
    // #region agent log
    fetch('http://127.0.0.1:7706/ingest/90bcaec2-2b39-4d4a-84b5-157c12735440', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Debug-Session-Id': 'fc0b35',
      },
      body: JSON.stringify({
        sessionId: 'fc0b35',
        runId: 'tab-busy-glow',
        hypothesisId: 'H7',
        location: 'AgentDockThreadTabbar.vue:busyThreadIds',
        message: 'conversation tabs busy glow set',
        data: {
          busyCount: ids.size,
          busyThreadIds: [...ids].slice(0, 8),
          liveBusyEmployeeIds: liveBusyEmployeeIds.value.slice(0, 8),
          openTabCount: openTabs.value.length,
        },
        timestamp: Date.now(),
      }),
    }).catch(() => {});
    // #endregion
  },
  { immediate: true },
);

function threadFailureHoverTitle(threadId: string, fallbackTitle: string): string {
  return threadFailureDetailById.value.get(threadId) ?? fallbackTitle;
}
const activeThreadId = computed(() => shell.activeIdeThreadId);
const canCloseTab = computed(() => openTabs.value.length > 1);
const showScrollControls = computed(() => canScrollLeft.value || canScrollRight.value);

function selectThread(threadId: string): void {
  void shell.selectIdeThread(threadId);
  historyOpen.value = false;
}

async function createThread(): Promise<void> {
  await shell.createIdeThread();
  historyOpen.value = false;
}

function toggleHistory(event: MouseEvent): void {
  event.stopPropagation();
  historyOpen.value = !historyOpen.value;
}

function closeTab(event: MouseEvent, threadId: string): void {
  event.stopPropagation();
  void shell.closeIdeThreadTab(threadId);
}

function handleDocumentClick(event: MouseEvent): void {
  const target = event.target;
  if (target instanceof Node && menuRef.value?.contains(target)) {
    return;
  }
  historyOpen.value = false;
}

function updateScrollState(): void {
  const scroller = tabsRef.value;
  if (!scroller) {
    canScrollLeft.value = false;
    canScrollRight.value = false;
    return;
  }
  const maxScroll = scroller.scrollWidth - scroller.clientWidth;
  canScrollLeft.value = scroller.scrollLeft > 1;
  canScrollRight.value = maxScroll > 1 && scroller.scrollLeft < maxScroll - 1;
}

/** Vertical wheel / trackpad → horizontal tab scroll when the strip overflows. */
function handleTabsWheel(event: WheelEvent): void {
  const scroller = tabsRef.value;
  if (!scroller) {
    return;
  }
  if (scroller.scrollWidth <= scroller.clientWidth + 1) {
    return;
  }
  const delta =
    Math.abs(event.deltaX) > Math.abs(event.deltaY) ? event.deltaX : event.deltaY;
  if (!delta) {
    return;
  }
  event.preventDefault();
  scroller.scrollLeft += delta;
  updateScrollState();
}

function tabScrollBehavior(): ScrollBehavior {
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth';
}

function scrollTabsBy(direction: -1 | 1): void {
  const scroller = tabsRef.value;
  if (!scroller) {
    return;
  }
  const step = Math.max(140, Math.floor(scroller.clientWidth * 0.7));
  scroller.scrollBy({ left: direction * step, behavior: tabScrollBehavior() });
  window.setTimeout(updateScrollState, 180);
}

function scrollActiveTabIntoView(): void {
  const scroller = tabsRef.value;
  if (!scroller || !activeThreadId.value) {
    return;
  }
  const active = scroller.querySelector<HTMLElement>(
    `[data-thread-id="${CSS.escape(activeThreadId.value)}"]`,
  );
  active?.scrollIntoView({
    behavior: tabScrollBehavior(),
    inline: 'nearest',
    block: 'nearest',
  });
  window.setTimeout(updateScrollState, 180);
}

function handleDocumentKeydown(event: KeyboardEvent): void {
  if (event.key === 'Escape' && historyOpen.value) {
    historyOpen.value = false;
  }
}

watch(activeThreadId, async () => {
  await nextTick();
  scrollActiveTabIntoView();
});

watch(
  openTabs,
  async () => {
    await nextTick();
    updateScrollState();
    scrollActiveTabIntoView();
  },
  { deep: true },
);

onMounted(() => {
  document.addEventListener('click', handleDocumentClick);
  document.addEventListener('keydown', handleDocumentKeydown);
  const scroller = tabsRef.value;
  scroller?.addEventListener('scroll', updateScrollState, { passive: true });
  window.addEventListener('resize', updateScrollState);
  // Bootstrap already hydrates IDE chat; avoid a second hydrate flash here.
  void nextTick(() => {
    updateScrollState();
    scrollActiveTabIntoView();
  });
});

onUnmounted(() => {
  document.removeEventListener('click', handleDocumentClick);
  document.removeEventListener('keydown', handleDocumentKeydown);
  tabsRef.value?.removeEventListener('scroll', updateScrollState);
  window.removeEventListener('resize', updateScrollState);
});
</script>

<template>
  <div
    ref="menuRef"
    class="agent-dock-thread-tabbar editor-tabbar editor-tabbar--mockup"
  >
    <button
      v-if="showScrollControls"
      type="button"
      class="agent-dock-thread-tabbar__scroll"
      :disabled="!canScrollLeft"
      aria-label="Scroll tabs left"
      title="Scroll tabs left"
      @click="scrollTabsBy(-1)"
    >
      ‹
    </button>

    <div
      ref="tabsRef"
      class="editor-tabbar__tabs agent-dock-thread-tabbar__tabs"
      role="tablist"
      aria-label="Open agent chats"
      @wheel="handleTabsWheel"
      @scroll="updateScrollState"
    >
      <button
        v-for="thread in openTabs"
        :key="thread.thread_id"
        type="button"
        role="tab"
        class="editor-tabbar__tab hud-active-chip hud-active-chip--tab agent-dock-thread-tabbar__tab"
        :class="{
          'editor-tabbar__tab--active hud-active-chip--active agent-dock-thread-tabbar__tab--active':
            activeThreadId === thread.thread_id,
          'agent-dock-thread-tabbar__tab--failed': threadFailureHintById.has(thread.thread_id),
          'agent-dock-thread-tabbar__tab--busy': busyThreadIds.has(thread.thread_id),
        }"
        :data-thread-id="thread.thread_id"
        :aria-selected="activeThreadId === thread.thread_id"
        :aria-label="
          busyThreadIds.has(thread.thread_id)
            ? `Busy — ${ideThreadTabTitle(thread.preview_label)}`
            : threadFailureHintById.get(thread.thread_id)
              ? `Last shift failed — ${ideThreadTabTitle(thread.preview_label)}`
              : ideThreadTabTitle(thread.preview_label)
        "
        :title="
          threadFailureHoverTitle(
            thread.thread_id,
            busyThreadIds.has(thread.thread_id)
              ? `Busy — ${ideThreadTabTitle(thread.preview_label)}`
              : ideThreadTabTitle(thread.preview_label),
          )
        "
        @click="selectThread(thread.thread_id)"
      >
        <WorkspaceIcon class="agent-dock-thread-tabbar__tab-icon" kind="chat" :size="12" />
        <span
          v-if="busyThreadIds.has(thread.thread_id)"
          class="agent-dock-thread-tabbar__tab-busy-mark"
          aria-hidden="true"
          title="Busy"
        >
          ●
        </span>
        <span
          v-else-if="threadFailureHintById.has(thread.thread_id)"
          class="agent-dock-thread-tabbar__tab-fail-mark"
          aria-hidden="true"
          title="Last shift failed"
        >
          !
        </span>
        <span class="editor-tabbar__label agent-dock-thread-tabbar__tab-label">
          {{ ideThreadTabTitle(thread.preview_label) }}
        </span>
        <span
          v-if="canCloseTab"
          role="button"
          tabindex="-1"
          class="agent-dock-thread-tabbar__tab-close"
          :aria-label="`Close ${ideThreadTabTitle(thread.preview_label)}`"
          @click="closeTab($event, thread.thread_id)"
        >
          <WorkbenchIcon name="close" class="editor-tabbar__close-icon" :size="11" />
        </span>
      </button>
    </div>

    <button
      v-if="showScrollControls"
      type="button"
      class="agent-dock-thread-tabbar__scroll"
      :disabled="!canScrollRight"
      aria-label="Scroll tabs right"
      title="Scroll tabs right"
      @click="scrollTabsBy(1)"
    >
      ›
    </button>

    <div class="editor-tabbar__tools agent-dock-thread-tabbar__tools">
      <div class="agent-dock-thread-tabbar__history">
        <button
          type="button"
          class="editor-tabbar__tool-button agent-dock-thread-tabbar__tool-button"
          :class="{ 'is-active': historyOpen }"
          aria-label="Chat history"
          :aria-expanded="historyOpen"
          aria-haspopup="listbox"
          title="Chat history"
          @click.stop="toggleHistory"
        >
          <WorkbenchIcon name="history" class="editor-tabbar__tool" />
        </button>

        <div
          v-if="historyOpen"
          class="agent-dock-thread-tabbar__history-panel"
          role="listbox"
          aria-label="Agent chat history"
        >
          <button
            type="button"
            class="agent-dock-thread-tabbar__history-new"
            @click.stop="createThread"
          >
            + New chat
          </button>
          <button
            v-for="thread in allThreads"
            :key="thread.thread_id"
            type="button"
            role="option"
            class="agent-dock-thread-tabbar__history-item"
            :class="{
              'agent-dock-thread-tabbar__history-item--active':
                activeThreadId === thread.thread_id,
              'agent-dock-thread-tabbar__history-item--failed':
                threadFailureHintById.has(thread.thread_id),
              'agent-dock-thread-tabbar__history-item--busy': busyThreadIds.has(
                thread.thread_id,
              ),
            }"
            :aria-selected="activeThreadId === thread.thread_id"
            :aria-label="
              threadFailureHintById.get(thread.thread_id)
                ? `Last shift failed — ${ideThreadMenuLabel(thread)}`
                : busyThreadIds.has(thread.thread_id)
                  ? `Busy — ${ideThreadMenuLabel(thread)}`
                  : ideThreadMenuLabel(thread)
            "
            :title="
              threadFailureHoverTitle(thread.thread_id, ideThreadMenuLabel(thread))
            "
            @click="selectThread(thread.thread_id)"
          >
            <span class="agent-dock-thread-tabbar__history-copy">
              <span class="agent-dock-thread-tabbar__history-label-row">
                <span
                  v-if="threadFailureHintById.has(thread.thread_id)"
                  class="agent-dock-thread-tabbar__history-fail-mark"
                  aria-hidden="true"
                >
                  !
                </span>
                <span class="agent-dock-thread-tabbar__history-label">
                  {{ ideThreadMenuLabel(thread) }}
                </span>
              </span>
              <span class="agent-dock-thread-tabbar__history-meta">
                {{ ideThreadMenuMeta(thread) }}
              </span>
            </span>
            <span
              v-if="activeThreadId === thread.thread_id"
              class="agent-dock-thread-tabbar__history-dot"
              aria-hidden="true"
            />
          </button>
        </div>
      </div>

      <button
        type="button"
        class="editor-tabbar__tool-button agent-dock-thread-tabbar__tool-button"
        aria-label="New chat"
        title="New chat"
        @click.stop="createThread"
      >
        <WorkbenchIcon name="plus" class="editor-tabbar__tool" />
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue';

import WorkbenchIcon from '../WorkbenchIcon.vue';
import WorkspaceIcon from '../WorkspaceIcon.vue';
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

const openTabs = computed(() => shell.openIdeThreadTabsForCurrentWorkspace);
const allThreads = computed(() =>
  sortIdeThreadsNewestFirst(shell.ideThreadsForCurrentWorkspace),
);
const activeThreadId = computed(() => shell.activeIdeThreadId);
const canCloseTab = computed(() => openTabs.value.length > 1);

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

onMounted(() => {
  document.addEventListener('click', handleDocumentClick);
  const workspaceId = shell.currentWorkspace?.workspace_id;
  if (workspaceId) {
    void shell.hydrateWorkspaceIdeChat(workspaceId);
  }
});

onUnmounted(() => {
  document.removeEventListener('click', handleDocumentClick);
});
</script>

<template>
  <div
    ref="menuRef"
    class="agent-dock-thread-tabbar editor-tabbar editor-tabbar--mockup"
  >
    <div class="editor-tabbar__tabs agent-dock-thread-tabbar__tabs" role="tablist" aria-label="Open agent chats">
      <button
        v-for="thread in openTabs"
        :key="thread.thread_id"
        type="button"
        role="tab"
        class="editor-tabbar__tab hud-active-chip hud-active-chip--tab agent-dock-thread-tabbar__tab"
        :class="{
          'editor-tabbar__tab--active hud-active-chip--active agent-dock-thread-tabbar__tab--active':
            activeThreadId === thread.thread_id,
        }"
        :aria-selected="activeThreadId === thread.thread_id"
        :title="ideThreadTabTitle(thread.preview_label)"
        @click="selectThread(thread.thread_id)"
      >
        <WorkspaceIcon class="agent-dock-thread-tabbar__tab-icon" kind="chat" :size="12" />
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
            }"
            :aria-selected="activeThreadId === thread.thread_id"
            @click="selectThread(thread.thread_id)"
          >
            <span class="agent-dock-thread-tabbar__history-copy">
              <span class="agent-dock-thread-tabbar__history-label">
                {{ ideThreadMenuLabel(thread) }}
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

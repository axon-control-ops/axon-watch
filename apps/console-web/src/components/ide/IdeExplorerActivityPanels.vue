<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue';

import {
  effectiveRequiredConnectorsUnavailable,
  isLegacyConnectorGlanceVisible,
} from '../../lib/connector-glance-view';
import {
  buildIdeGitPanelCaption,
  buildIdeSearchPanelCaption,
  countIdeDirtyFileTabs,
  ideActivityPanelCollapseAriaLabel,
  ideGitPanelCaptionUsesLiveRegion,
  ideGitPanelListAriaLabel,
  ideSearchPanelCaptionUsesLiveRegion,
  ideSearchPanelResultsAriaLabel,
  ideSearchPanelRetryAriaLabel,
  clampIdeSearchPanelHighlightIndex,
  resolveIdeGitPanelEnterDocumentId,
  resolveIdeSearchPanelEnterPath,
  resolveIdeSearchPanelEscapeAction,
  stepIdeSearchPanelHighlightIndex,
  shouldShowIdeGitPanelList,
  shouldShowIdeSearchPanelResults,
  shouldShowIdeSearchPanelRetry,
  shouldShowIdeSearchPanelAttention,
} from '../../lib/ide-activity-panel-view';
import type { WorkspaceDocumentDescriptor } from '../../lib/workspace-documents';
import { editorDocumentResourcePath } from '../../lib/editor-tab-labels';
import {
  buildIdeRunPanelConnectorNotice,
  buildIdeTerminalSidebarStub,
  ideSidebarStubActionAriaLabel,
  ideSidebarStubUsesLiveRegion,
} from '../../lib/ide-sidebar-stub-view';
import {
  ensureWatchConnectorsLoaded,
  ensureWorkspaceFilesLoaded,
  openWatchConnectors,
} from '../../composables/useIdeEditorStatusBar';
import { shouldOfferRunStop } from '../../lib/run-lifecycle-ui';
import { useShellStore } from '../../stores/shell';

const shell = useShellStore();
const searchQuery = ref('');
const searchHighlightIndex = ref(0);
const searchInputRef = ref<HTMLInputElement | null>(null);
const searchListRef = ref<HTMLElement | null>(null);
const gitHighlightIndex = ref(0);
const gitPanelRef = ref<HTMLElement | null>(null);
const gitListRef = ref<HTMLElement | null>(null);

function scrollActiveListItemIntoView(list: HTMLElement | null): void {
  if (!list) {
    return;
  }

  list
    .querySelector<HTMLElement>('[aria-current="true"]')
    ?.scrollIntoView({ block: 'nearest', inline: 'nearest' });
}

const searchResults = computed(() => {
  const query = searchQuery.value.trim().toLowerCase();
  if (!query) {
    return shell.workspaceFileEntries.slice(0, 24);
  }
  return shell.workspaceFileEntries
    .filter((entry) => entry.path.toLowerCase().includes(query))
    .slice(0, 32);
});

const searchHasWorkspace = computed(() => Boolean(shell.currentWorkspace?.workspace_id));

const searchCaption = computed(() =>
  buildIdeSearchPanelCaption({
    query: searchQuery.value,
    resultCount: searchResults.value.length,
    loadState: shell.workspaceFilesLoadState,
    hasWorkspace: searchHasWorkspace.value,
  }),
);

const searchResultsVisible = computed(() =>
  shouldShowIdeSearchPanelResults({
    resultCount: searchResults.value.length,
    loadState: shell.workspaceFilesLoadState,
    hasWorkspace: searchHasWorkspace.value,
  }),
);

const searchRetryVisible = computed(() =>
  shouldShowIdeSearchPanelRetry({
    loadState: shell.workspaceFilesLoadState,
    hasWorkspace: searchHasWorkspace.value,
  }),
);

const searchAttentionVisible = computed(() =>
  shouldShowIdeSearchPanelAttention({
    loadState: shell.workspaceFilesLoadState,
    hasWorkspace: searchHasWorkspace.value,
  }),
);

const searchCaptionLive = computed(() =>
  ideSearchPanelCaptionUsesLiveRegion({
    loadState: shell.workspaceFilesLoadState,
    hasWorkspace: searchHasWorkspace.value,
  }),
);

const searchResultsAriaLabel = computed(() =>
  ideSearchPanelResultsAriaLabel({
    resultCount: searchResults.value.length,
    query: searchQuery.value,
  }),
);

const searchRetryLoading = computed(() => shell.workspaceFilesLoadState === 'loading');

const searchRetryAriaLabel = computed(() => ideSearchPanelRetryAriaLabel(searchRetryLoading.value));

const dirtyDocuments = computed(() =>
  shell.editorDocuments.filter((document) => document.source === 'file' && document.dirty),
);

const dirtyFileCount = computed(() => countIdeDirtyFileTabs(shell.editorDocuments));

const gitPanelCaption = computed(() => buildIdeGitPanelCaption(dirtyFileCount.value));

const gitPanelListVisible = computed(() =>
  shouldShowIdeGitPanelList(dirtyFileCount.value),
);

const gitPanelListAriaLabel = computed(() => ideGitPanelListAriaLabel(dirtyFileCount.value));

const gitCaptionLive = computed(() => ideGitPanelCaptionUsesLiveRegion(dirtyFileCount.value));

const terminalSidebarStub = computed(() =>
  buildIdeTerminalSidebarStub({
    terminalVisible: shell.workbenchTerminalPanelVisible,
    runPhase: shell.primaryActiveRun?.phase ?? null,
  }),
);

const watchConnected = computed(() => shell.runtimeSummary?.watch.connected ?? false);

const runConnectorNotice = computed(() =>
  buildIdeRunPanelConnectorNotice({
    watchConnected: watchConnected.value,
    requiredConnectorsUnavailable: effectiveRequiredConnectorsUnavailable(
      shell.connectorsSummary,
      watchConnected.value,
    ),
    legacyConnectorGlanceVisible: isLegacyConnectorGlanceVisible({
      connectorsLoadState: shell.connectorsLoadState,
      items: shell.connectorsItems,
      summary: shell.connectorsSummary,
      watchConnected: watchConnected.value,
      layoutMode: 'ide',
    }),
  }),
);

function toggleTerminalFromStub(): void { shell.toggleIdeTerminalPanel(); }

function openConnectorsFromRunNotice(): void {
  openWatchConnectors(shell);
}

function openSearchResult(path: string): void {
  void shell.openWorkspaceFile(path);
}

function retrySearchLoad(): void {
  ensureWorkspaceFilesLoaded(shell);
}

function handleGitPanelKeydown(event: KeyboardEvent): void {
  if (event.key === 'Escape') {
    event.preventDefault();
    shell.toggleIdeExplorer();
    return;
  }

  if (!gitPanelListVisible.value || dirtyDocuments.value.length === 0) {
    return;
  }

  if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
    event.preventDefault();
    gitHighlightIndex.value = stepIdeSearchPanelHighlightIndex({
      currentIndex: gitHighlightIndex.value,
      direction: event.key === 'ArrowDown' ? 'down' : 'up',
      resultCount: dirtyDocuments.value.length,
    });
    return;
  }

  if (event.key !== 'Enter') {
    return;
  }

  const documentId = resolveIdeGitPanelEnterDocumentId({
    documents: dirtyDocuments.value,
    listVisible: gitPanelListVisible.value,
    highlightIndex: gitHighlightIndex.value,
  });
  if (documentId) {
    event.preventDefault();
    shell.setActiveEditorDocument(documentId);
  }
}

function handleSearchInputKeydown(event: KeyboardEvent): void {
  if (event.isComposing) {
    return;
  }

  if (event.key === 'Escape') {
    const action = resolveIdeSearchPanelEscapeAction(searchQuery.value);
    event.preventDefault();
    if (action === 'clear-query') {
      searchQuery.value = '';
      searchInputRef.value?.focus();
      return;
    }
    shell.toggleIdeExplorer();
    return;
  }

  if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
    if (!searchResultsVisible.value || searchResults.value.length === 0) {
      return;
    }

    event.preventDefault();
    searchHighlightIndex.value = stepIdeSearchPanelHighlightIndex({
      currentIndex: searchHighlightIndex.value,
      direction: event.key === 'ArrowDown' ? 'down' : 'up',
      resultCount: searchResults.value.length,
    });
    return;
  }

  if (event.key !== 'Enter') {
    return;
  }

  const path = resolveIdeSearchPanelEnterPath({
    results: searchResults.value,
    resultsVisible: searchResultsVisible.value,
    highlightIndex: searchHighlightIndex.value,
  });
  if (path) {
    event.preventDefault();
    openSearchResult(path);
  }
}

function gitPanelRowLabel(document: WorkspaceDocumentDescriptor): string {
  return editorDocumentResourcePath(document);
}

watch(
  () =>
    shell.ideActivityView === 'run' &&
    !shell.ideExplorerCollapsed &&
    runConnectorNotice.value !== null,
  (shouldRefresh) => {
    if (shouldRefresh) {
      ensureWatchConnectorsLoaded(shell);
    }
  },
  { immediate: true },
);

watch(
  () => shell.ideActivityView === 'search' && !shell.ideExplorerCollapsed,
  (active) => {
    if (active) {
      ensureWorkspaceFilesLoaded(shell);
    }
  },
  { immediate: true },
);

watch(
  () => shell.ideActivityView === 'search' && !shell.ideExplorerCollapsed,
  async (active) => {
    if (!active) {
      return;
    }
    await nextTick();
    searchInputRef.value?.focus();
  },
);

watch(
  () => shell.ideActivityView === 'git' && !shell.ideExplorerCollapsed,
  async (active) => {
    if (!active) {
      return;
    }
    await nextTick();
    gitPanelRef.value?.focus();
  },
);

watch(dirtyDocuments, (documents) => {
  gitHighlightIndex.value = clampIdeSearchPanelHighlightIndex(
    gitHighlightIndex.value,
    documents.length,
  );
});

watch(searchQuery, () => {
  searchHighlightIndex.value = 0;
});

watch(searchResults, (results) => {
  searchHighlightIndex.value = clampIdeSearchPanelHighlightIndex(
    searchHighlightIndex.value,
    results.length,
  );
});

watch(
  () =>
    [
      searchHighlightIndex.value,
      searchResultsVisible.value,
      searchResults.value.length,
    ] as const,
  async () => {
    if (!searchResultsVisible.value || searchResults.value.length === 0) {
      return;
    }
    await nextTick();
    scrollActiveListItemIntoView(searchListRef.value);
  },
);

watch(
  () => [gitHighlightIndex.value, gitPanelListVisible.value, dirtyDocuments.value.length] as const,
  async () => {
    if (!gitPanelListVisible.value || dirtyDocuments.value.length === 0) {
      return;
    }
    await nextTick();
    scrollActiveListItemIntoView(gitListRef.value);
  },
);
</script>

<template>
  <section
    v-if="shell.ideActivityView === 'search'"
    class="ide-explorer-panel ide-explorer-panel--stub hud-panel-frame"
    :class="{ 'ide-explorer-panel--search-attention': searchAttentionVisible }"
  >
    <div class="panel-heading ide-explorer-panel__heading">
      <p class="panel-heading__title">SEARCH</p>
      <button
        type="button"
        class="panel-heading__action ide-explorer-panel__collapse"
        :aria-label="ideActivityPanelCollapseAriaLabel('search')"
        :title="ideActivityPanelCollapseAriaLabel('search')"
        @click="shell.toggleIdeExplorer()"
      >
        ‹
      </button>
    </div>
    <div class="ide-panel-search">
      <input
        ref="searchInputRef"
        v-model="searchQuery"
        class="ide-panel-search__input"
        type="search"
        aria-label="Search file paths"
        placeholder="Search file paths..."
        :disabled="!searchHasWorkspace"
        @keydown="handleSearchInputKeydown"
      />
      <p
        v-if="searchCaption"
        class="region-copy ide-panel-caption"
        :role="searchCaptionLive ? 'status' : undefined"
        :aria-live="searchCaptionLive ? 'polite' : undefined"
      >
        {{ searchCaption }}
      </p>
      <button
        v-if="searchRetryVisible"
        type="button"
        class="ide-panel-retry"
        :disabled="searchRetryLoading"
        :aria-label="searchRetryAriaLabel"
        @click="retrySearchLoad"
      >
        {{ searchRetryLoading ? 'RETRYING…' : 'RETRY' }}
      </button>
      <ul
        v-if="searchResultsVisible"
        ref="searchListRef"
        class="ide-panel-list"
        :aria-label="searchResultsAriaLabel"
      >
        <li v-for="(entry, index) in searchResults" :key="entry.path">
          <button
            type="button"
            class="ide-panel-list__button"
            :class="{ 'ide-panel-list__button--active': index === searchHighlightIndex }"
            :aria-current="index === searchHighlightIndex ? 'true' : undefined"
            @click="openSearchResult(entry.path)"
          >
            {{ entry.path }}
          </button>
        </li>
      </ul>
    </div>
  </section>

  <section
    v-else-if="shell.ideActivityView === 'git'"
    ref="gitPanelRef"
    class="ide-explorer-panel ide-explorer-panel--stub hud-panel-frame"
    :class="{ 'ide-explorer-panel--git-attention': gitPanelListVisible }"
    tabindex="-1"
    @keydown="handleGitPanelKeydown"
  >
    <div class="panel-heading ide-explorer-panel__heading">
      <p class="panel-heading__title">SOURCE CONTROL</p>
      <button
        type="button"
        class="panel-heading__action ide-explorer-panel__collapse"
        :aria-label="ideActivityPanelCollapseAriaLabel('git')"
        :title="ideActivityPanelCollapseAriaLabel('git')"
        @click="shell.toggleIdeExplorer()"
      >
        ‹
      </button>
    </div>
    <div class="ide-panel-search">
      <p
        class="region-copy ide-panel-caption"
        :role="gitCaptionLive ? 'status' : undefined"
        :aria-live="gitCaptionLive ? 'polite' : undefined"
      >
        {{ gitPanelCaption }}
      </p>
      <ul
        v-if="gitPanelListVisible"
        ref="gitListRef"
        class="ide-panel-list"
        :aria-label="gitPanelListAriaLabel"
      >
        <li v-for="(document, index) in dirtyDocuments" :key="document.id">
          <button
            type="button"
            class="ide-panel-list__button ide-panel-list__button--dirty"
            :class="{ 'ide-panel-list__button--active': index === gitHighlightIndex }"
            :aria-current="index === gitHighlightIndex ? 'true' : undefined"
            :aria-label="`Open ${gitPanelRowLabel(document)}`"
            @click="shell.setActiveEditorDocument(document.id)"
          >
            {{ gitPanelRowLabel(document) }}
          </button>
        </li>
      </ul>
    </div>
  </section>

  <section
    v-else-if="shell.ideActivityView === 'run'"
    class="ide-explorer-panel ide-explorer-panel--stub hud-panel-frame"
    :class="runConnectorNotice ? `ide-explorer-panel--stub-${runConnectorNotice.tone}` : undefined"
  >
    <div class="panel-heading ide-explorer-panel__heading">
      <p class="panel-heading__title">RUN</p>
      <button
        type="button"
        class="panel-heading__action ide-explorer-panel__collapse"
        :aria-label="ideActivityPanelCollapseAriaLabel('run')"
        :title="ideActivityPanelCollapseAriaLabel('run')"
        @click="shell.toggleIdeExplorer()"
      >
        ‹
      </button>
    </div>
    <div
      v-if="runConnectorNotice"
      class="ide-explorer-panel__stub-body ide-explorer-panel__run-notice"
      :role="runConnectorNotice.tone === 'attention' ? 'status' : undefined"
      :aria-live="runConnectorNotice.tone === 'attention' ? 'polite' : undefined"
    >
      <p
        v-for="(line, index) in runConnectorNotice.lines"
        :key="index"
        class="region-copy ide-explorer-panel__stub-copy"
      >
        {{ line }}
      </p>
      <button
        type="button"
        class="ide-explorer-panel__stub-action"
        :aria-label="`${runConnectorNotice.actionLabel} in Mission Control connectors`"
        @click="openConnectorsFromRunNotice"
      >
        {{ runConnectorNotice.actionLabel }}
      </button>
    </div>
    <div class="ide-panel-search">
      <p class="region-copy ide-panel-caption">
        {{ shell.primaryActiveRun ? `${shell.primaryActiveRun.run_id} · ${shell.primaryActiveRun.phase}` : 'No active run' }}
      </p>
      <p v-if="shell.primaryActiveRun" class="region-copy ide-panel-caption">
        {{ shell.primaryActiveRun.summary }}
      </p>
      <button
        v-if="shouldOfferRunStop(shell.primaryActiveRun?.can_stop)"
        type="button"
        class="ide-panel-action"
        :disabled="!shell.canStopPrimaryRun"
        @click="shell.stopPrimaryRun()"
      >
        {{ shell.runMutationState === 'stopping' ? 'STOPPING…' : 'STOP RUN' }}
      </button>
    </div>
  </section>

  <section
    v-else-if="shell.ideActivityView === 'terminal'"
    class="ide-explorer-panel ide-explorer-panel--stub hud-panel-frame"
    :class="`ide-explorer-panel--stub-${terminalSidebarStub.tone}`"
  >
    <div class="panel-heading ide-explorer-panel__heading">
      <p class="panel-heading__title">TERMINAL</p>
      <button
        type="button"
        class="panel-heading__action ide-explorer-panel__collapse"
        :aria-label="ideActivityPanelCollapseAriaLabel('terminal')"
        :title="ideActivityPanelCollapseAriaLabel('terminal')"
        @click="shell.toggleIdeExplorer()"
      >
        ‹
      </button>
    </div>
    <div
      class="ide-explorer-panel__stub-body"
      :role="
        ideSidebarStubUsesLiveRegion(terminalSidebarStub.tone, 'terminal') ? 'status' : undefined
      "
      :aria-live="
        ideSidebarStubUsesLiveRegion(terminalSidebarStub.tone, 'terminal') ? 'polite' : undefined
      "
    >
      <p
        v-for="(line, index) in terminalSidebarStub.lines"
        :key="index"
        class="region-copy ide-explorer-panel__stub-copy"
      >
        {{ line }}
      </p>
      <button
        v-if="terminalSidebarStub.actionLabel"
        type="button"
        class="ide-explorer-panel__stub-action"
        :aria-label="
          ideSidebarStubActionAriaLabel(terminalSidebarStub.actionLabel, 'terminal')
        "
        @click="toggleTerminalFromStub"
      >
        {{ terminalSidebarStub.actionLabel }}
      </button>
    </div>
  </section>
</template>

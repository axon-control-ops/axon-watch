<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import type { ResearchTranscriptItem } from '../../lib/agent-transcript-blocks';
import { researchFaviconUrl, researchHostname } from '../../lib/research-favicon';
import { canFlyToWorkspaceSource } from '../../lib/research-fly-to-source';
import { researchBlockPreview } from '../../lib/prove-research-source';
import {
  formatResearchKindLabel,
  formatResearchProviderLabel,
  type ResearchBlockKind,
} from '../../lib/research-provider';
import { sanitizeResearchCardTitle, sanitizeResearchSnippet } from '../../lib/research-snippet';
import { useShellStore } from '../../stores/shell';

const SEARCH_SNIPPET_COLLAPSE_AT = 180;
const FETCH_SNIPPET_COLLAPSE_AT = 320;

const props = defineProps<{
  query: string;
  items: ResearchTranscriptItem[];
  live?: boolean;
  provider?: string;
  kind?: ResearchBlockKind;
}>();

const shell = useShellStore();
const expandedCards = ref<Set<number>>(new Set());
const blockCollapsed = ref(Boolean(!props.live && props.items.length > 0));

const providerLabel = computed(() => formatResearchProviderLabel(props.provider ?? ''));
const kindLabel = computed(() => formatResearchKindLabel(props.kind));
const blockPreview = computed(() =>
  researchBlockPreview({
    query: props.query,
    items: props.items,
    kind: props.kind,
    provider: props.provider,
    live: props.live,
  }),
);
const canCollapse = computed(() => !props.live && props.items.length > 0);

const renderedItems = computed(() =>
  props.items.map((item) => {
    const snippet = sanitizeResearchSnippet(item.snippet);
    const hostname = researchHostname(item.url);
    const hasUrl = Boolean(item.url && item.url !== 'about:blank');
    return {
      title: sanitizeResearchCardTitle(item.title, snippet, item.url),
      snippet,
      hostname,
      favicon: researchFaviconUrl(item.url),
      url: item.url,
      hasUrl,
    };
  }),
);

watch(
  () => props.live,
  (live) => {
    if (live) {
      blockCollapsed.value = false;
    } else if (props.items.length > 0) {
      blockCollapsed.value = true;
    }
  },
);

function collapseAt(): number {
  return props.kind === 'fetch' ? FETCH_SNIPPET_COLLAPSE_AT : SEARCH_SNIPPET_COLLAPSE_AT;
}

function toggleBlock(): void {
  blockCollapsed.value = !blockCollapsed.value;
}

function toggleCard(index: number): void {
  const next = new Set(expandedCards.value);
  if (next.has(index)) {
    next.delete(index);
  } else {
    next.add(index);
  }
  expandedCards.value = next;
}

function snippetNeedsExpand(snippet: string): boolean {
  const limit = collapseAt();
  return snippet.length > limit || snippet.split('\n').length > (props.kind === 'fetch' ? 4 : 3);
}

function snippetPreview(snippet: string): string {
  const limit = collapseAt();
  if (snippet.length <= limit) {
    return snippet;
  }
  return `${snippet.slice(0, limit).trim()}…`;
}

function openInBrowser(url: string): void {
  if (!url || url === 'about:blank') {
    return;
  }
  window.open(url, '_blank', 'noopener,noreferrer');
}

function proveSource(item: {
  title: string;
  url: string;
  snippet: string;
}): void {
  shell.proveResearchSource({
    title: item.title,
    url: item.url,
    snippet: item.snippet,
    query: props.query,
    kind: props.kind,
  });
}

function openInEditor(item: { title: string; url: string; snippet: string }): void {
  shell.openResearchInEditor({
    title: item.title,
    url: item.url,
    snippet: item.snippet,
  });
}

function canFlyToSource(item: { title: string; url: string; snippet: string }): boolean {
  return canFlyToWorkspaceSource({
    title: item.title,
    url: item.url,
    snippet: item.snippet,
    query: props.query,
  });
}
</script>

<template>
  <div
    class="agent-block agent-block--research"
    :class="{ 'agent-block--research-collapsed': blockCollapsed && canCollapse }"
  >
    <button
      v-if="canCollapse"
      type="button"
      class="agent-block__research-block-toggle"
      @click="toggleBlock"
    >
      <span class="agent-block__research-block-icon" aria-hidden="true">
        {{ blockCollapsed ? '▸' : '▾' }}
      </span>
      <span class="agent-block__research-icon" aria-hidden="true">⌕</span>
      <span class="agent-block__research-query">{{ blockPreview }}</span>
      <span v-if="kindLabel" class="agent-block__research-kind">{{ kindLabel }}</span>
      <span v-if="providerLabel" class="agent-block__research-provider">{{ providerLabel }}</span>
    </button>

    <div v-else class="agent-block__research-header">
      <span class="agent-block__research-icon" aria-hidden="true">⌕</span>
      <span class="agent-block__research-query">{{ query }}</span>
      <span v-if="kindLabel" class="agent-block__research-kind">{{ kindLabel }}</span>
      <span v-if="providerLabel" class="agent-block__research-provider">{{ providerLabel }}</span>
      <span v-if="live" class="agent-block__research-live">searching…</span>
    </div>

    <div v-show="!blockCollapsed || live" class="agent-block__research-body">
      <ul v-if="renderedItems.length" class="agent-block__research-list">
        <li
          v-for="(item, index) in renderedItems"
          :key="`${item.url}:${index}`"
          class="agent-block__research-card hud-panel-frame"
          :class="{
            'agent-block__research-card--expanded': expandedCards.has(index),
            'agent-block__research-card--fetch': kind === 'fetch',
          }"
        >
          <div class="agent-block__research-card-head">
            <img
              v-if="item.favicon"
              class="agent-block__research-favicon"
              :src="item.favicon"
              alt=""
              width="16"
              height="16"
              loading="lazy"
              decoding="async"
            />
            <span
              v-else
              class="agent-block__research-favicon agent-block__research-favicon--fallback"
              aria-hidden="true"
            >↗</span>
            <button
              type="button"
              class="agent-block__research-card-title-wrap agent-block__research-prove"
              @click="proveSource(item)"
            >
              <span class="agent-block__research-title">
                {{ item.title }}
              </span>
              <span v-if="item.hostname" class="agent-block__research-url">
                {{ item.hostname }}
              </span>
            </button>
            <button
              v-if="canFlyToSource(item)"
              type="button"
              class="agent-block__research-editor"
              title="Jump to workspace source"
              aria-label="Jump to workspace source"
              @click.stop="proveSource(item)"
            >
              SRC
            </button>
            <button
              v-if="kind === 'fetch' && item.snippet"
              type="button"
              class="agent-block__research-editor"
              title="Open in editor"
              aria-label="Open in editor"
              @click.stop="openInEditor(item)"
            >
              ED
            </button>
            <button
              v-if="item.hasUrl"
              type="button"
              class="agent-block__research-open"
              title="Open in browser"
              aria-label="Open in browser"
              @click.stop="openInBrowser(item.url)"
            >
              ↗
            </button>
          </div>
          <template v-if="item.snippet">
            <div
              v-if="snippetNeedsExpand(item.snippet)"
              class="agent-block__research-snippet-toggle"
              role="button"
              tabindex="0"
              @click="toggleCard(index)"
              @keydown.enter.prevent="toggleCard(index)"
              @keydown.space.prevent="toggleCard(index)"
            >
              <pre
                v-if="kind === 'fetch'"
                class="agent-block__research-fetch-body"
                :class="{ 'agent-block__research-fetch-body--collapsed': !expandedCards.has(index) }"
              >{{ expandedCards.has(index) ? item.snippet : snippetPreview(item.snippet) }}</pre>
              <p
                v-else
                class="agent-block__research-snippet"
              >
                {{ expandedCards.has(index) ? item.snippet : snippetPreview(item.snippet) }}
              </p>
              <span class="agent-block__research-expand">
                {{ expandedCards.has(index) ? 'Show less' : 'Show more' }}
              </span>
            </div>
            <template v-else>
              <pre
                v-if="kind === 'fetch'"
                class="agent-block__research-fetch-body"
              >{{ item.snippet }}</pre>
              <p v-else class="agent-block__research-snippet">{{ item.snippet }}</p>
            </template>
          </template>
        </li>
      </ul>
      <p v-else-if="live" class="agent-block__research-empty">Gathering sources…</p>
    </div>
  </div>
</template>

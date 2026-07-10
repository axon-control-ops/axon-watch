<script setup lang="ts">
import { computed, ref } from 'vue';

import { probeSentryWriteScope, resolveSentryIssue } from '../../api/sentry-api';
import {
  sentryIssuesFromSignalMeta,
  type SentrySignalIssue,
} from '../../lib/sentry-signal-issues-view';
import { useShellStore } from '../../stores/shell';

const props = defineProps<{
  meta: Record<string, unknown> | null | undefined;
  compact?: boolean;
}>();

const shell = useShellStore();
const resolvingId = ref<string | null>(null);
const errorMessage = ref<string | null>(null);
const statusMessage = ref<string | null>(null);
const resolvedIds = ref<string[]>([]);
const writeScopeHint = ref<string | null>(null);

const issues = computed(() => sentryIssuesFromSignalMeta(props.meta ?? null));

const visibleIssues = computed(() =>
  issues.value.filter((issue) => !resolvedIds.value.includes(issue.id)),
);

async function refreshSignalsQuietly(): Promise<void> {
  // Background briefing refresh avoids a full Attention reload flash; the Axon
  // aggregate signal correctly remains while other Sentry issues are still open.
  await Promise.all([
    shell.loadInbox(),
    shell.loadOperatorBriefing({ background: true }),
    shell.loadRuntimeSummary({ background: true }),
  ]);
}

async function handleResolve(issue: SentrySignalIssue): Promise<void> {
  if (resolvingId.value) {
    return;
  }
  resolvingId.value = issue.id;
  errorMessage.value = null;
  writeScopeHint.value = null;
  statusMessage.value = null;
  const label = issue.shortId || issue.id;
  try {
    const result = await resolveSentryIssue(issue.id);
    if (!result.ok) {
      if (result.reason === 'missing_write_scope') {
        writeScopeHint.value =
          'Sentry token needs event:write or project:write. Update the token in /vault.';
      }
      errorMessage.value =
        result.detail ||
        result.reason ||
        `Resolve failed for ${label}`;
      return;
    }
    resolvedIds.value = [...resolvedIds.value, issue.id];
    const remaining = Math.max(0, visibleIssues.value.length - 1);
    statusMessage.value =
      remaining > 0
        ? `Resolved ${label} in Sentry. Axon alert stays until the other ${remaining} issue${remaining === 1 ? '' : 's'} are resolved (or CLEAR locally).`
        : `Resolved ${label} in Sentry. Refreshing monitor…`;
    await refreshSignalsQuietly();
    if (visibleIssues.value.length === 0) {
      statusMessage.value = `Resolved ${label} in Sentry. If the Axon alert remains, wait for the next monitor poll or CLEAR locally.`;
    }
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Sentry resolve failed';
    try {
      const probe = await probeSentryWriteScope();
      if (!probe.write_scope) {
        writeScopeHint.value =
          probe.detail ||
          'Sentry write probe failed — check event:write / project:write on the vault token.';
      }
    } catch {
      // Probe is diagnostic only.
    }
  } finally {
    resolvingId.value = null;
  }
}
</script>

<template>
  <div v-if="issues.length || statusMessage" class="sentry-issues-list">
    <p class="sentry-issues-list__label">Sentry issues</p>
    <p class="sentry-issues-list__hint">
      Resolve writes to Sentry per issue. The Axon critical signal stays while any unresolved issues remain — CLEAR only dismisses Axon locally.
    </p>
    <ul v-if="visibleIssues.length" class="sentry-issues-list__items">
      <li
        v-for="issue in visibleIssues"
        :key="issue.id"
        class="sentry-issues-list__item"
      >
        <div class="sentry-issues-list__copy">
          <a
            v-if="issue.permalink"
            class="sentry-issues-list__title"
            :href="issue.permalink"
            target="_blank"
            rel="noopener noreferrer"
            @click.stop
          >
            {{ issue.shortId || issue.id }} · {{ issue.title }}
          </a>
          <span v-else class="sentry-issues-list__title">
            {{ issue.shortId || issue.id }} · {{ issue.title }}
          </span>
          <span class="sentry-issues-list__meta">
            <template v-if="issue.level">{{ issue.level }} · </template>
            {{ issue.count }} event{{ issue.count === 1 ? '' : 's' }}
          </span>
        </div>
        <button
          type="button"
          class="sentry-issues-list__resolve"
          :class="{ 'sentry-issues-list__resolve--compact': compact }"
          :disabled="resolvingId !== null"
          title="Resolve this issue in Sentry (does not CLEAR the local Axon signal)"
          @click.stop="handleResolve(issue)"
        >
          {{ resolvingId === issue.id ? 'Resolving…' : 'Resolve' }}
        </button>
      </li>
    </ul>
    <p v-if="statusMessage" class="sentry-issues-list__status" role="status">{{ statusMessage }}</p>
    <p v-if="errorMessage" class="sentry-issues-list__error" role="alert">{{ errorMessage }}</p>
    <p v-if="writeScopeHint" class="sentry-issues-list__hint">{{ writeScopeHint }}</p>
  </div>
</template>

<style scoped>
.sentry-issues-list {
  display: grid;
  gap: 0.45rem;
  margin-top: 0.55rem;
}

.sentry-issues-list__label {
  margin: 0;
  font-size: 0.62rem;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  opacity: 0.72;
}

.sentry-issues-list__items {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 0.4rem;
}

.sentry-issues-list__item {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.55rem;
}

.sentry-issues-list__copy {
  display: grid;
  gap: 0.15rem;
  min-width: 0;
}

.sentry-issues-list__title {
  color: inherit;
  font-size: 0.72rem;
  line-height: 1.3;
  text-decoration: none;
  word-break: break-word;
}

a.sentry-issues-list__title:hover {
  text-decoration: underline;
}

.sentry-issues-list__meta {
  font-size: 0.62rem;
  opacity: 0.7;
}

.sentry-issues-list__resolve {
  flex: 0 0 auto;
  border: 1px solid rgba(255, 176, 72, 0.4);
  border-radius: 0.35rem;
  background: rgba(255, 176, 72, 0.1);
  color: inherit;
  cursor: pointer;
  font: inherit;
  font-size: 0.68rem;
  letter-spacing: 0.04em;
  padding: 0.3rem 0.55rem;
}

.sentry-issues-list__resolve--compact {
  font-size: 0.62rem;
  padding: 0.24rem 0.45rem;
}

.sentry-issues-list__resolve:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.sentry-issues-list__error,
.sentry-issues-list__hint,
.sentry-issues-list__status {
  margin: 0;
  font-size: 0.66rem;
  line-height: 1.35;
}

.sentry-issues-list__error {
  color: #ff8f8f;
}

.sentry-issues-list__status {
  color: rgba(72, 255, 196, 0.92);
}

.sentry-issues-list__hint {
  opacity: 0.8;
}
</style>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';

import { fetchClaudeRuntimeStatus, fetchCodexRuntimeStatus, fetchCursorRuntimeStatus } from '../../api/runtime-api';
import { fetchWorkspaceComposerPrefs, saveWorkspaceComposerPrefs } from '../../api/workspace-api';
import { buildClaudeCatalogRows } from '../../lib/claude-catalog-view';
import { buildCodexCatalogRows } from '../../lib/codex-catalog-view';
import { buildCursorCatalogRows, type CursorCatalogRow } from '../../lib/cursor-catalog-view';
import { useShellStore } from '../../stores/shell';

type RuntimeFamily = 'cursor' | 'claude' | 'codex';

const RUNTIME_FAMILIES: { id: RuntimeFamily; label: string; hint: string }[] = [
  { id: 'cursor', label: 'Cursor CLI', hint: 'Cursor Agent / composer shifts' },
  { id: 'claude', label: 'Claude Code CLI', hint: 'Claude Code agent shifts' },
  { id: 'codex', label: 'Codex CLI', hint: 'OpenAI Codex agent shifts' },
];

const shell = useShellStore();

const loadState = ref<'idle' | 'loading' | 'loaded' | 'error'>('idle');
const saving = ref(false);
const actionMessage = ref<string | null>(null);
const actionTone = ref<'idle' | 'ok' | 'error' | 'pending'>('idle');

const autoAllowedRuntimes = ref<string[]>([]);
const maxConcurrentRuntimes = ref<1 | 'multiple'>(1);
const runtimeModels = ref<Record<RuntimeFamily, string>>({
  cursor: 'auto',
  claude: 'auto',
  codex: 'auto',
});

const modelCatalog = ref<Record<RuntimeFamily, CursorCatalogRow[]>>({
  cursor: [],
  claude: [],
  codex: [],
});

const workspaceId = computed(() => shell.currentWorkspace?.workspace_id ?? null);
const workspaceLabel = computed(
  () => shell.currentWorkspace?.display_name ?? shell.currentWorkspace?.workspace_id ?? '—',
);

const allRuntimesAllowed = computed(
  () => autoAllowedRuntimes.value.length === 0,
);

function toggleRuntime(family: RuntimeFamily): void {
  const idx = autoAllowedRuntimes.value.indexOf(family);
  if (idx === -1) {
    autoAllowedRuntimes.value = [...autoAllowedRuntimes.value, family];
  } else {
    autoAllowedRuntimes.value = autoAllowedRuntimes.value.filter((r) => r !== family);
  }
}

function setAllRuntimes(): void {
  autoAllowedRuntimes.value = [];
}

function setRuntimeModel(family: RuntimeFamily, modelId: string): void {
  runtimeModels.value = { ...runtimeModels.value, [family]: modelId || 'auto' };
}

async function loadCatalogs(): Promise<void> {
  const [cursorStatus, claudeStatus, codexStatus] = await Promise.allSettled([
    fetchCursorRuntimeStatus(),
    fetchClaudeRuntimeStatus(),
    fetchCodexRuntimeStatus(),
  ]);
  modelCatalog.value = {
    cursor: buildCursorCatalogRows(cursorStatus.status === 'fulfilled' ? cursorStatus.value : null),
    claude: buildClaudeCatalogRows(claudeStatus.status === 'fulfilled' ? claudeStatus.value : null),
    codex: buildCodexCatalogRows(codexStatus.status === 'fulfilled' ? codexStatus.value : null),
  };
}

async function load(): Promise<void> {
  const id = workspaceId.value;
  if (!id) {
    return;
  }
  loadState.value = 'loading';
  try {
    const [prefs] = await Promise.all([fetchWorkspaceComposerPrefs(id), loadCatalogs()]);
    autoAllowedRuntimes.value = prefs.auto_allowed_runtimes ?? [];
    maxConcurrentRuntimes.value = (prefs.max_concurrent_runtimes ?? 1) > 1 ? 'multiple' : 1;
    runtimeModels.value = {
      cursor: prefs.cursor_cli_model || 'auto',
      claude: prefs.claude_cli_model || 'auto',
      codex: prefs.codex_cli_model || 'auto',
    };
    loadState.value = 'loaded';
  } catch (error) {
    loadState.value = 'error';
    actionTone.value = 'error';
    actionMessage.value = error instanceof Error ? error.message : 'Could not load runtime policy.';
  }
}

async function save(): Promise<void> {
  const id = workspaceId.value;
  if (!id) {
    return;
  }
  saving.value = true;
  actionTone.value = 'pending';
  actionMessage.value = 'Saving…';
  try {
    await saveWorkspaceComposerPrefs(id, {
      auto_allowed_runtimes: autoAllowedRuntimes.value,
      max_concurrent_runtimes: maxConcurrentRuntimes.value === 'multiple' ? 4 : 1,
      cursor_cli_model: runtimeModels.value.cursor,
      claude_cli_model: runtimeModels.value.claude,
      codex_cli_model: runtimeModels.value.codex,
    });
    await shell.loadWorkspaces({ sync: false });
    actionTone.value = 'ok';
    actionMessage.value = 'Runtime policy saved.';
  } catch (error) {
    actionTone.value = 'error';
    actionMessage.value = error instanceof Error ? error.message : 'Save failed.';
  } finally {
    saving.value = false;
  }
}

onMounted(() => {
  void load();
});
</script>

<template>
  <div class="workspace-runtime-policy">
    <p
      v-if="actionMessage"
      class="settings-feedback-banner settings-feedback-banner--inline"
      :class="{
        'settings-feedback-banner--error': actionTone === 'error',
        'settings-feedback-banner--ok': actionTone === 'ok',
        'settings-feedback-banner--pending': actionTone === 'pending',
      }"
      role="status"
      aria-live="polite"
    >
      {{ actionMessage }}
    </p>

    <p v-if="loadState === 'loading'" class="workspace-runtime-policy__empty">
      Loading policy for {{ workspaceLabel }}…
    </p>

    <template v-else-if="loadState !== 'error'">

      <section class="operator-settings-form__section">
        <header class="operator-settings-form__section-header">
          <h2>AUTO mode — allowed runtimes</h2>
          <p>
            Which CLIs the continuous worker scheduler is allowed to use when
            dispatching autonomous shifts for
            <strong>{{ workspaceLabel }}</strong>.
            Runtimes not in this list will be skipped by AUTO dispatch
            (you can still use them manually from the Agent Dock).
          </p>
        </header>

        <div class="workspace-runtime-policy__runtime-list" role="group" aria-label="Allowed runtimes for AUTO mode">
          <label class="workspace-runtime-policy__runtime-row">
            <input
              type="checkbox"
              :checked="allRuntimesAllowed"
              :disabled="saving"
              @change="setAllRuntimes"
            />
            <span class="workspace-runtime-policy__runtime-copy">
              <span class="workspace-runtime-policy__runtime-label">All runtimes</span>
              <span class="workspace-runtime-policy__runtime-hint">Any signed-in CLI may run worker shifts</span>
            </span>
          </label>

          <div
            v-for="rt in RUNTIME_FAMILIES"
            :key="rt.id"
            class="workspace-runtime-policy__runtime-row"
            :class="{ 'workspace-runtime-policy__runtime-row--active': autoAllowedRuntimes.includes(rt.id) }"
          >
            <label class="workspace-runtime-policy__runtime-row-main">
              <input
                type="checkbox"
                :checked="autoAllowedRuntimes.includes(rt.id)"
                :disabled="saving"
                @change="toggleRuntime(rt.id)"
              />
              <span class="workspace-runtime-policy__runtime-copy">
                <span class="workspace-runtime-policy__runtime-label">{{ rt.label }}</span>
                <span class="workspace-runtime-policy__runtime-hint">{{ rt.hint }}</span>
              </span>
            </label>

            <label class="workspace-runtime-policy__runtime-model">
              <span class="workspace-runtime-policy__runtime-model-label">Model</span>
              <select
                :value="runtimeModels[rt.id]"
                :disabled="saving"
                @change="setRuntimeModel(rt.id, ($event.target as HTMLSelectElement).value)"
              >
                <option value="auto">Auto</option>
                <option
                  v-for="model in modelCatalog[rt.id]"
                  :key="model.id"
                  :value="model.id"
                  :disabled="model.available === false"
                >
                  {{ model.label }}
                </option>
              </select>
            </label>
          </div>
        </div>

        <p class="workspace-runtime-policy__note" role="note">
          Pin the exact model each runtime dispatches with for AUTO shifts in
          <strong>{{ workspaceLabel }}</strong>. "Auto" leaves the choice to that
          runtime's own default routing.
        </p>

        <p class="workspace-runtime-policy__note" role="note">
          Selecting specific runtimes overrides "All runtimes." Uncheck all three to
          go back to unrestricted.
        </p>
      </section>

      <section class="operator-settings-form__section">
        <header class="operator-settings-form__section-header">
          <h2>Workspace concurrency</h2>
          <p>
            How many agent shifts may run at the same time for
            <strong>{{ workspaceLabel }}</strong>.
            Single prevents checkout race conditions. Multiple allows
            parallel throughput but uses proportionally more quota and RAM.
          </p>
        </header>

        <div class="workspace-runtime-policy__concurrency-choices" role="radiogroup" aria-label="Workspace concurrency">
          <label
            class="workspace-runtime-policy__concurrency-choice"
            :class="{ 'workspace-runtime-policy__concurrency-choice--active': maxConcurrentRuntimes === 1 }"
          >
            <input
              type="radio"
              name="max-concurrent"
              value="1"
              :checked="maxConcurrentRuntimes === 1"
              :disabled="saving"
              @change="maxConcurrentRuntimes = 1"
            />
            <span class="workspace-runtime-policy__concurrency-copy">
              <span class="workspace-runtime-policy__concurrency-label">Single (1 at a time)</span>
              <span class="workspace-runtime-policy__concurrency-hint">
                One shift runs per workspace — no checkout conflicts.
                Recommended default.
              </span>
            </span>
          </label>

          <label
            class="workspace-runtime-policy__concurrency-choice"
            :class="{ 'workspace-runtime-policy__concurrency-choice--active': maxConcurrentRuntimes === 'multiple' }"
          >
            <input
              type="radio"
              name="max-concurrent"
              value="multiple"
              :checked="maxConcurrentRuntimes === 'multiple'"
              :disabled="saving"
              @change="maxConcurrentRuntimes = 'multiple'"
            />
            <span class="workspace-runtime-policy__concurrency-copy">
              <span class="workspace-runtime-policy__concurrency-label">Multiple (up to max active)</span>
              <span class="workspace-runtime-policy__concurrency-hint">
                Parallel shifts, each in an isolated checkout. Faster
                throughput — set "Max active agents" in the Agents panel to
                cap total spend.
              </span>
            </span>
          </label>
        </div>
      </section>

      <div class="workspace-runtime-policy__actions">
        <button
          type="button"
          class="operator-settings-form__button operator-settings-form__button--primary"
          :disabled="saving"
          @click="save"
        >
          {{ saving ? 'Saving…' : 'Save runtime policy' }}
        </button>
        <button
          type="button"
          class="operator-settings-form__button operator-settings-form__button--ghost"
          :disabled="saving"
          @click="load"
        >
          Reset
        </button>
      </div>

    </template>
  </div>
</template>

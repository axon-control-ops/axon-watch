<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';

import type { RuntimeTargetRecord } from '../../api/control-plane';
import {
  logoutClaudeRuntime,
  logoutCodexRuntime,
  logoutCursorRuntime,
  startClaudeRuntimeLogin,
  startCodexRuntimeLogin,
  startCursorRuntimeLogin,
} from '../../api/control-plane';
import { navigateToAppSurface } from '../../lib/app-surface-route';
import {
  runtimeAuthAccountLabel,
  runtimeAuthMethodLabel,
  runtimeAuthSummary,
} from '../../lib/runtime-auth-view';
import { useShellStore } from '../../stores/shell';
import ClaudeUsageCard from './ClaudeUsageCard.vue';
import CodexUsageCard from './CodexUsageCard.vue';
import CursorUsageCard from './CursorUsageCard.vue';
import WorkspaceAutonomyTogglePanel from './WorkspaceAutonomyTogglePanel.vue';
import WorkspaceRuntimePolicyPanel from './WorkspaceRuntimePolicyPanel.vue';

type RuntimeFamily = 'cursor' | 'claude' | 'codex';

type RuntimeCard = {
  family: RuntimeFamily;
  title: string;
  subtitle: string;
  installed: boolean;
  loggedIn: boolean;
  ready: boolean;
  method: string;
  account: string;
  summary: string;
  statusCommand: string;
  loginCommand: string;
  canSignIn: boolean;
  canStartCliLogin: boolean;
  canSignOut: boolean;
  canShowSignOutHelp: boolean;
  managedByVault: boolean;
  hostProfileAuth: boolean;
  accountScopeNote: string;
  statusTone: 'ready' | 'warn' | 'muted';
  statusLabel: string;
};

const shell = useShellStore();
const actionPending = ref<RuntimeFamily | null>(null);
const actionMessage = ref<string | null>(null);
const actionTone = ref<'idle' | 'ok' | 'error' | 'pending'>('idle');
const copiedCommand = ref<string | null>(null);

const isLoading = computed(() => shell.runtimeStatusLoadState === 'loading' && !shell.runtimeStatus);
const runtimeTargets = computed(() => [
  ...(shell.runtimeStatus?.local ?? []),
  ...(shell.runtimeStatus?.cloud ?? []),
]);
const runtimeCards = computed(() => buildCards());
const autoOverrideEnabled = computed(
  () => shell.operatorPresenceSettings.auto_composer_runtime_override_enabled,
);
const autoOverrideTarget = computed(
  () => shell.operatorPresenceSettings.auto_composer_runtime_target,
);
const autoOverrideEffective = computed(
  () =>
    shell.operatorPresenceSettings.autonomy_mode === 'full' &&
    autoOverrideEnabled.value &&
    Boolean(autoOverrideTarget.value.trim()),
);
const selectedAutoOverrideTarget = computed(() => {
  const targetId = autoOverrideTarget.value.trim();
  return runtimeTargets.value.find((record) => record.id === targetId) ?? null;
});
const autoOverrideSummary = computed(() => {
  if (!autoOverrideEnabled.value) {
    return 'Off — composers keep their manual per-thread runtime selections.';
  }
  if (!autoOverrideTarget.value.trim()) {
    return 'Choose a runtime target before Full Auto can override composers.';
  }
  const target = selectedAutoOverrideTarget.value;
  const label = target ? `${target.label} (${runtimeStatusLine(target)})` : autoOverrideTarget.value;
  if (shell.operatorPresenceSettings.autonomy_mode !== 'full') {
    return `${label} is armed, but it only applies when VAXON is on Full Auto.`;
  }
  return `${label} is controlling all composers while VAXON is on Full Auto.`;
});

function shortenBinaryPath(path: string): string {
  const trimmed = path.trim();
  if (!trimmed) {
    return 'Not installed on host';
  }
  const parts = trimmed.split('/').filter(Boolean);
  if (parts.length <= 2) {
    return trimmed;
  }
  return `…/${parts.slice(-2).join('/')}`;
}

function buildCards(): RuntimeCard[] {
  return (['cursor', 'claude', 'codex'] as RuntimeFamily[]).map((family) => {
    const target =
      runtimeTargets.value.find(
        (record) => record.family === family && record.target_type === 'local',
      ) ??
      runtimeTargets.value.find((record) => record.family === family) ??
      null;
    return buildCard(family, target);
  });
}

function familyTitle(family: RuntimeFamily): string {
  if (family === 'cursor') return 'Cursor CLI';
  if (family === 'claude') return 'Claude Code CLI';
  return 'Codex CLI';
}

function familyLoginCommand(family: RuntimeFamily, binary = ''): string {
  if (family === 'cursor') {
    const name = binary.trim().split('/').pop()?.toLowerCase() ?? '';
    if (name === 'cursor-agent' || name.startsWith('cursor-agent.')) {
      return 'cursor-agent login';
    }
    return 'cursor agent login';
  }
  if (family === 'claude') return 'claude auth login';
  return 'codex login';
}

function familyStatusCommand(family: RuntimeFamily, binary = ''): string {
  if (family === 'cursor') {
    const name = binary.trim().split('/').pop()?.toLowerCase() ?? '';
    if (name === 'cursor-agent' || name.startsWith('cursor-agent.')) {
      return 'cursor-agent status';
    }
    return 'cursor agent status';
  }
  if (family === 'claude') return 'claude auth status';
  return 'codex login status';
}

function buildCard(family: RuntimeFamily, target: RuntimeTargetRecord | null): RuntimeCard {
  const auth = target?.auth;
  const loggedIn = Boolean(auth?.logged_in);
  const installed = Boolean(target?.available && target.binary);
  const managedByVault =
    auth?.auth_method === 'vault_api_key' || auth?.auth_method === 'api_key';
  const oauthBacked = ['oauth', 'chatgpt', 'claude.ai'].includes(
    String(auth?.auth_method ?? '').trim().toLowerCase(),
  );
  const title = familyTitle(family);
  const binary = target?.binary ?? '';
  const loginCommand = familyLoginCommand(family, binary);
  const statusCommand = familyStatusCommand(family, binary);

  let statusTone: RuntimeCard['statusTone'] = 'muted';
  let statusLabel = 'Not installed';
  if (installed && loggedIn) {
    statusTone = 'ready';
    statusLabel = 'Signed in';
  } else if (installed) {
    statusTone = 'warn';
    statusLabel = 'Needs sign-in';
  }

  return {
    family,
    title,
    subtitle: shortenBinaryPath(target?.binary ?? ''),
    installed,
    loggedIn,
    ready: Boolean(target?.ready),
    method: runtimeAuthMethodLabel(auth?.auth_method),
    account: runtimeAuthAccountLabel(auth),
    summary: runtimeAuthSummary(auth) || 'Status unavailable',
    statusCommand,
    loginCommand,
    canSignIn: installed && !loggedIn,
    canStartCliLogin: installed && managedByVault,
    canSignOut: false,
    canShowSignOutHelp: installed && loggedIn && (managedByVault || oauthBacked),
    managedByVault,
    hostProfileAuth: oauthBacked,
    accountScopeNote:
      installed && loggedIn && oauthBacked
        ? `${title} browser login is shared by this host profile. To use another account, manually sign out of the host profile first or configure the second account through Vault/API-key auth where supported.`
        : '',
    statusTone,
    statusLabel,
  };
}

async function refreshStatus(): Promise<void> {
  actionTone.value = 'pending';
  actionMessage.value = 'Refreshing runtime auth…';
  try {
    await Promise.all([shell.loadRuntimeStatus(true), shell.loadCursorCatalog(true)]);
    if (shell.runtimeStatusLoadState === 'error') {
      actionTone.value = 'error';
      actionMessage.value = shell.runtimeStatusError ?? 'Runtime status refresh failed.';
      return;
    }
    actionTone.value = 'ok';
    actionMessage.value = 'Runtime auth refreshed.';
  } catch (error) {
    actionTone.value = 'error';
    actionMessage.value =
      error instanceof Error ? error.message : 'Runtime status refresh failed.';
  }
}

async function runAction(family: RuntimeFamily, action: 'login' | 'logout'): Promise<void> {
  actionPending.value = family;
  actionTone.value = 'pending';
  actionMessage.value = null;
  try {
    const result =
      family === 'cursor'
        ? action === 'login'
          ? await startCursorRuntimeLogin()
          : await logoutCursorRuntime()
        : family === 'claude'
          ? action === 'login'
            ? await startClaudeRuntimeLogin()
            : await logoutClaudeRuntime()
          : action === 'login'
            ? await startCodexRuntimeLogin()
            : await logoutCodexRuntime();
    actionTone.value = result.status === 'error' ? 'error' : 'ok';
    actionMessage.value =
      result.account_scope_notice && !result.message.includes(result.account_scope_notice)
        ? `${result.message} ${result.account_scope_notice}`
        : result.message;
    await Promise.all([shell.loadRuntimeStatus(true), shell.loadCursorCatalog(true)]);
  } catch (error) {
    actionTone.value = 'error';
    actionMessage.value =
      error instanceof Error ? error.message : 'Runtime auth action failed.';
  } finally {
    actionPending.value = null;
  }
}

async function copyCommand(command: string): Promise<void> {
  try {
    await navigator.clipboard.writeText(command);
    copiedCommand.value = command;
    window.setTimeout(() => {
      if (copiedCommand.value === command) {
        copiedCommand.value = null;
      }
    }, 1600);
  } catch {
    copiedCommand.value = null;
  }
}

function runtimeStatusLine(record: RuntimeTargetRecord): string {
  if (record.ready) return 'Ready';
  if (!record.available) return 'Not installed';
  return record.auth.message || 'Installed but not ready';
}

async function setAutoOverrideEnabled(enabled: boolean): Promise<void> {
  const fallbackTarget =
    autoOverrideTarget.value.trim() ||
    shell.selectedRuntimeTargetId ||
    shell.runtimeStatus?.default_runtime ||
    runtimeTargets.value[0]?.id ||
    '';
  await shell.saveOperatorPresenceSettingsPatch({
    auto_composer_runtime_override_enabled: enabled,
    auto_composer_runtime_target: enabled ? fallbackTarget : autoOverrideTarget.value,
  });
}

async function onAutoOverrideToggle(event: Event): Promise<void> {
  const checked = (event.target as HTMLInputElement).checked;
  try {
    await setAutoOverrideEnabled(checked);
  } catch {
    // Settings banner in the shell owns the durable error; keep the switch controlled by store state.
  }
}

async function onAutoOverrideTargetChange(event: Event): Promise<void> {
  const target = (event.target as HTMLSelectElement).value;
  try {
    await shell.saveOperatorPresenceSettingsPatch({
      auto_composer_runtime_target: target,
    });
  } catch {
    // Settings banner in the shell owns the durable error.
  }
}

onMounted(() => {
  void Promise.all([shell.loadRuntimeStatus(true), shell.loadCursorCatalog(true)]);
});
</script>

<template>
  <div class="runtime-auth-settings">
    <div class="settings-section-toolbar">
      <p class="settings-section-toolbar__copy">
        Host CLI sessions used by Agent dispatch. Sign-in opens a browser on this machine.
      </p>
      <button
        type="button"
        class="operator-settings-form__button operator-settings-form__button--ghost"
        :disabled="shell.runtimeStatusLoadState === 'loading' || actionPending !== null"
        @click="refreshStatus"
      >
        {{ shell.runtimeStatusLoadState === 'loading' ? 'Refreshing…' : 'Refresh' }}
      </button>
    </div>

    <p
      v-if="actionMessage"
      class="settings-feedback-banner"
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

    <div v-if="isLoading" class="runtime-auth-settings__grid">
      <article v-for="index in 2" :key="index" class="runtime-auth-settings__card runtime-auth-settings__card--loading">
        <div class="runtime-auth-settings__skeleton runtime-auth-settings__skeleton--title" />
        <div class="runtime-auth-settings__skeleton runtime-auth-settings__skeleton--line" />
        <div class="runtime-auth-settings__skeleton runtime-auth-settings__skeleton--line" />
      </article>
    </div>

    <CursorUsageCard
      v-if="!isLoading"
      class="runtime-auth-settings__usage"
      :usage="shell.runtimeStatus?.cursor_usage"
    />

    <ClaudeUsageCard
      v-if="!isLoading"
      class="runtime-auth-settings__usage"
      :usage="shell.runtimeStatus?.claude_usage"
    />

    <CodexUsageCard
      v-if="!isLoading"
      class="runtime-auth-settings__usage"
      :usage="shell.runtimeStatus?.codex_usage"
    />

    <section v-if="!isLoading" class="runtime-auth-settings__policy-section">
      <header class="runtime-auth-settings__policy-header">
        <h2>Full Auto composer runtime</h2>
        <p>
          Temporarily force every IDE composer and continuous worker onto one runtime while
          VAXON is on Full Auto. Manual per-thread choices are preserved and return when this
          toggle or Full Auto is off.
        </p>
      </header>
      <label class="operator-settings-form__row">
        <input
          type="checkbox"
          :checked="autoOverrideEnabled"
          :disabled="shell.operatorPresenceSettingsSaving"
          @change="onAutoOverrideToggle"
        />
        <span class="operator-settings-form__copy">
          <strong>Override all composers during Full Auto</strong>
          <small>{{ autoOverrideSummary }}</small>
        </span>
      </label>
      <label class="operator-settings-form__row operator-settings-form__row--select">
        <span class="operator-settings-form__copy">
          <strong>Runtime to use in Auto</strong>
          <small>
            This does not erase manual composer selections; it only masks them while active.
          </small>
        </span>
        <select
          class="operator-settings-form__select"
          :value="autoOverrideTarget"
          :disabled="shell.operatorPresenceSettingsSaving || !autoOverrideEnabled"
          @change="onAutoOverrideTargetChange"
        >
          <option value="">Use each composer's manual runtime</option>
          <option
            v-for="target in runtimeTargets"
            :key="target.id"
            :value="target.id"
          >
            {{ target.label }} · {{ runtimeStatusLine(target) }}
          </option>
        </select>
      </label>
      <p
        class="settings-feedback-banner settings-feedback-banner--inline"
        :class="{
          'settings-feedback-banner--ok': autoOverrideEffective,
          'settings-feedback-banner--pending': autoOverrideEnabled && !autoOverrideEffective,
        }"
        role="status"
      >
        {{ autoOverrideSummary }}
      </p>
    </section>

    <div v-if="!isLoading" class="runtime-auth-settings__grid">
      <article
        v-for="card in runtimeCards"
        :key="card.family"
        class="runtime-auth-settings__card"
        :class="`runtime-auth-settings__card--${card.statusTone}`"
      >
        <header class="runtime-auth-settings__card-header">
          <div class="runtime-auth-settings__card-title">
            <span class="runtime-auth-settings__glyph" aria-hidden="true">
              {{ card.family === 'cursor' ? '◈' : '◇' }}
            </span>
            <div>
              <h3>{{ card.title }}</h3>
              <p :title="card.subtitle.startsWith('…/') ? card.summary : undefined">
                {{ card.subtitle }}
              </p>
            </div>
          </div>
          <span
            class="runtime-auth-settings__badge"
            :class="`runtime-auth-settings__badge--${card.statusTone}`"
          >
            {{ card.statusLabel }}
          </span>
        </header>

        <div class="runtime-auth-settings__hero">
          <p class="runtime-auth-settings__account">
            {{ card.account || card.summary }}
          </p>
          <p v-if="card.method" class="runtime-auth-settings__method">{{ card.method }}</p>
        </div>

        <div class="runtime-auth-settings__probe">
          <span class="runtime-auth-settings__probe-label">Verify on host</span>
          <div class="runtime-auth-settings__probe-row">
            <code>{{ card.statusCommand }}</code>
            <button
              type="button"
              class="runtime-auth-settings__copy"
              :title="`Copy ${card.statusCommand}`"
              @click="copyCommand(card.statusCommand)"
            >
              {{ copiedCommand === card.statusCommand ? 'Copied' : 'Copy' }}
            </button>
          </div>
        </div>

        <p v-if="card.managedByVault" class="runtime-auth-settings__note">
          Auth is vault-backed. Manage keys on
          <button type="button" class="runtime-auth-settings__inline-link" @click="navigateToAppSurface('vault')">
            Vault
          </button>
          instead of CLI sign-out.
        </p>
        <p v-else-if="card.hostProfileAuth" class="runtime-auth-settings__note">
          {{ card.accountScopeNote }} Axon-X shows sign-out help instead of running
          host-global logout automatically.
        </p>
        <p v-else-if="!card.installed" class="runtime-auth-settings__note">
          Install the CLI on the control-plane host, then refresh status.
        </p>
        <p v-else-if="card.accountScopeNote" class="runtime-auth-settings__note">
          {{ card.accountScopeNote }}
        </p>

        <div class="runtime-auth-settings__actions">
          <button
            v-if="card.canSignIn"
            type="button"
            class="operator-settings-form__button operator-settings-form__button--primary"
            :disabled="actionPending !== null"
            @click="runAction(card.family, 'login')"
          >
            {{ actionPending === card.family ? 'Opening login…' : 'Sign in' }}
          </button>
          <span
            v-else-if="card.loggedIn"
            class="runtime-auth-settings__connected-chip"
          >
            Connected
          </span>
          <button
            v-if="card.canStartCliLogin"
            type="button"
            class="operator-settings-form__button operator-settings-form__button--ghost"
            :disabled="actionPending !== null"
            @click="runAction(card.family, 'login')"
          >
            {{ actionPending === card.family ? 'Opening login…' : 'CLI sign in' }}
          </button>
          <button
            v-if="card.canSignOut"
            type="button"
            class="operator-settings-form__button operator-settings-form__button--ghost"
            :disabled="actionPending !== null"
            @click="runAction(card.family, 'logout')"
          >
            {{ actionPending === card.family ? 'Signing out…' : 'Sign out' }}
          </button>
          <button
            v-else-if="card.canShowSignOutHelp"
            type="button"
            class="operator-settings-form__button operator-settings-form__button--ghost"
            :disabled="actionPending !== null"
            @click="runAction(card.family, 'logout')"
          >
            {{ actionPending === card.family ? 'Checking…' : 'Host sign-out help' }}
          </button>
        </div>
      </article>
    </div>

    <div v-if="!isLoading" class="runtime-auth-settings__policy-section">
      <header class="runtime-auth-settings__policy-header"><h2>Workspace autonomy</h2><p>Turn AUTO dispatch on or off per workspace, without switching your active workspace to check each one.</p></header>
      <WorkspaceAutonomyTogglePanel />
    </div>

    <div v-if="!isLoading" class="runtime-auth-settings__policy-section">
      <header class="runtime-auth-settings__policy-header">
        <h2>Workspace runtime policy</h2>
        <p>Control which runtimes may run AUTO shifts and how many can run in parallel per workspace.</p>
      </header>
      <WorkspaceRuntimePolicyPanel />
    </div>
  </div>
</template>

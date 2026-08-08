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
import CursorUsageCard from './CursorUsageCard.vue';

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
  canSignOut: boolean;
  managedByVault: boolean;
  statusTone: 'ready' | 'warn' | 'muted';
  statusLabel: string;
};

const shell = useShellStore();
const actionPending = ref<RuntimeFamily | null>(null);
const actionMessage = ref<string | null>(null);
const actionTone = ref<'idle' | 'ok' | 'error' | 'pending'>('idle');
const copiedCommand = ref<string | null>(null);

const isLoading = computed(() => shell.runtimeStatusLoadState === 'loading' && !shell.runtimeStatus);
const runtimeCards = computed(() => buildCards());

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
  const targets = [...(shell.runtimeStatus?.local ?? []), ...(shell.runtimeStatus?.cloud ?? [])];
  return (['cursor', 'claude', 'codex'] as RuntimeFamily[]).map((family) => {
    const target =
      targets.find((record) => record.family === family && record.target_type === 'local') ??
      targets.find((record) => record.family === family) ??
      null;
    return buildCard(family, target);
  });
}

function familyTitle(family: RuntimeFamily): string {
  if (family === 'cursor') return 'Cursor CLI';
  if (family === 'claude') return 'Claude Code CLI';
  return 'Codex CLI';
}

function familyLoginCommand(family: RuntimeFamily): string {
  if (family === 'cursor') return 'cursor agent login';
  if (family === 'claude') return 'claude auth login';
  return 'codex login';
}

function familyStatusCommand(family: RuntimeFamily): string {
  if (family === 'cursor') return 'cursor agent status';
  if (family === 'claude') return 'claude auth status';
  return 'codex login status';
}

function buildCard(family: RuntimeFamily, target: RuntimeTargetRecord | null): RuntimeCard {
  const auth = target?.auth;
  const loggedIn = Boolean(auth?.logged_in);
  const installed = Boolean(target?.available && target.binary);
  const managedByVault =
    auth?.auth_method === 'vault_api_key' || auth?.auth_method === 'api_key';
  const title = familyTitle(family);
  const loginCommand = familyLoginCommand(family);
  const statusCommand = familyStatusCommand(family);

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
    canSignOut: installed && loggedIn && !managedByVault,
    managedByVault,
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
    actionMessage.value = result.message;
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
        <p v-else-if="!card.installed" class="runtime-auth-settings__note">
          Install the CLI on the control-plane host, then refresh status.
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
            v-if="card.canSignOut"
            type="button"
            class="operator-settings-form__button operator-settings-form__button--ghost"
            :disabled="actionPending !== null"
            @click="runAction(card.family, 'logout')"
          >
            {{ actionPending === card.family ? 'Signing out…' : 'Sign out' }}
          </button>
        </div>
      </article>
    </div>
  </div>
</template>

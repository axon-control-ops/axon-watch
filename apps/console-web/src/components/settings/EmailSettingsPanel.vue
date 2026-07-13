<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue';

import {
  deleteEmailAccount,
  fetchEmailSettings,
  patchEmailSettings,
  testEmailAccount,
  upsertEmailAccount,
  type EmailMailboxAccount,
  type EmailSettingsSnapshot,
} from '../../api/email-settings-api';
import { navigateToAppSurface } from '../../lib/app-surface-route';
import { useShellStore } from '../../stores/shell';

const shell = useShellStore();
const snapshot = ref<EmailSettingsSnapshot | null>(null);
const loadError = ref<string | null>(null);
const actionMessage = ref<string | null>(null);
const actionTone = ref<'idle' | 'ok' | 'error' | 'pending'>('idle');
const saving = ref(false);
const testingKey = ref<string | null>(null);

const form = reactive({
  account_id: '',
  workspace_id: '',
  email_address: '',
  display_name: '',
  imap_host: '',
  imap_port: 993,
  imap_username: '',
  imap_ssl: true,
  imap_folder: 'INBOX',
  smtp_host: '',
  smtp_port: 465,
  smtp_username: '',
  smtp_ssl: true,
  smtp_starttls: false,
  smtp_from_email: '',
  monitor_enabled: true,
  poll_seconds: 60,
  password_imap: '',
  password_smtp: '',
});

const workspaces = computed(() => shell.workspaces ?? []);
const accounts = computed(() => snapshot.value?.settings.accounts ?? []);
const auth = computed(() => snapshot.value?.auth ?? null);

function blankForm(workspaceId?: string): void {
  form.account_id = '';
  form.workspace_id = workspaceId || shell.currentWorkspace?.workspace_id || workspaces.value[0]?.workspace_id || '';
  form.email_address = '';
  form.display_name = '';
  form.imap_host = '';
  form.imap_port = 993;
  form.imap_username = '';
  form.imap_ssl = true;
  form.imap_folder = 'INBOX';
  form.smtp_host = '';
  form.smtp_port = 465;
  form.smtp_username = '';
  form.smtp_ssl = true;
  form.smtp_starttls = false;
  form.smtp_from_email = '';
  form.monitor_enabled = true;
  form.poll_seconds = 60;
  form.password_imap = '';
  form.password_smtp = '';
}

function prefill(account: EmailMailboxAccount): void {
  form.account_id = account.account_id;
  form.workspace_id = account.workspace_id;
  form.email_address = account.email_address;
  form.display_name = account.display_name;
  form.imap_host = account.imap.host;
  form.imap_port = account.imap.port;
  form.imap_username = account.imap.username;
  form.imap_ssl = account.imap.ssl;
  form.imap_folder = account.imap.folder || 'INBOX';
  form.smtp_host = account.smtp.host;
  form.smtp_port = account.smtp.port;
  form.smtp_username = account.smtp.username;
  form.smtp_ssl = account.smtp.ssl;
  form.smtp_starttls = account.smtp.starttls;
  form.smtp_from_email = account.smtp.from_email;
  form.monitor_enabled = account.monitor.enabled;
  form.poll_seconds = account.monitor.poll_seconds;
  form.password_imap = '';
  form.password_smtp = '';
}

async function reload(): Promise<void> {
  actionTone.value = 'pending';
  actionMessage.value = 'Loading email settings…';
  try {
    snapshot.value = await fetchEmailSettings();
    loadError.value = null;
    actionTone.value = 'ok';
    actionMessage.value = 'Email settings synced.';
    if (!form.workspace_id) {
      blankForm();
    }
  } catch (error) {
    loadError.value = error instanceof Error ? error.message : 'Email settings load failed';
    actionTone.value = 'error';
    actionMessage.value = loadError.value;
  }
}

async function saveBridgePrefs(): Promise<void> {
  if (!snapshot.value) return;
  saving.value = true;
  actionTone.value = 'pending';
  actionMessage.value = 'Saving bridge preferences…';
  try {
    snapshot.value = await patchEmailSettings({
      bridge_enabled: snapshot.value.settings.bridge_enabled,
      bridge_workspace_id: snapshot.value.settings.bridge_workspace_id,
      stub_enabled: snapshot.value.settings.stub_enabled,
      workspace_hint_map: snapshot.value.settings.workspace_hint_map,
    });
    actionTone.value = 'ok';
    actionMessage.value = 'Bridge preferences saved.';
  } catch (error) {
    actionTone.value = 'error';
    actionMessage.value = error instanceof Error ? error.message : 'Save failed';
  } finally {
    saving.value = false;
  }
}

async function saveMailbox(): Promise<void> {
  saving.value = true;
  actionTone.value = 'pending';
  actionMessage.value = 'Saving mailbox…';
  try {
    snapshot.value = await upsertEmailAccount({
      account_id: form.account_id || undefined,
      workspace_id: form.workspace_id,
      email_address: form.email_address,
      display_name: form.display_name,
      imap_host: form.imap_host,
      imap_port: Number(form.imap_port) || 993,
      imap_username: form.imap_username,
      imap_ssl: form.imap_ssl,
      imap_folder: form.imap_folder || 'INBOX',
      smtp_host: form.smtp_host,
      smtp_port: Number(form.smtp_port) || 465,
      smtp_username: form.smtp_username,
      smtp_ssl: form.smtp_ssl,
      smtp_starttls: form.smtp_starttls,
      smtp_from_email: form.smtp_from_email,
      monitor_enabled: form.monitor_enabled,
      poll_seconds: Number(form.poll_seconds) || 60,
      password_imap: form.password_imap,
      password_smtp: form.password_smtp,
    });
    actionTone.value = 'ok';
    actionMessage.value = `Mailbox saved for ${form.email_address}.`;
    form.password_imap = '';
    form.password_smtp = '';
  } catch (error) {
    actionTone.value = 'error';
    actionMessage.value = error instanceof Error ? error.message : 'Mailbox save failed';
  } finally {
    saving.value = false;
  }
}

async function runTest(accountId: string): Promise<void> {
  testingKey.value = accountId;
  actionTone.value = 'pending';
  actionMessage.value = 'Testing IMAP/SMTP…';
  try {
    const result = await testEmailAccount({
      account_id: accountId,
      password_imap: form.account_id === accountId ? form.password_imap : '',
      password_smtp: form.account_id === accountId ? form.password_smtp : '',
    });
    actionTone.value = result.ok ? 'ok' : 'error';
    actionMessage.value = `${result.imap.detail} · ${result.smtp.detail}`;
  } catch (error) {
    actionTone.value = 'error';
    actionMessage.value = error instanceof Error ? error.message : 'Mailbox test failed';
  } finally {
    testingKey.value = null;
  }
}

async function removeAccount(accountId: string): Promise<void> {
  saving.value = true;
  actionTone.value = 'pending';
  actionMessage.value = 'Removing mailbox…';
  try {
    snapshot.value = await deleteEmailAccount(accountId);
    if (form.account_id === accountId) {
      blankForm(form.workspace_id);
    }
    actionTone.value = 'ok';
    actionMessage.value = 'Mailbox removed.';
  } catch (error) {
    actionTone.value = 'error';
    actionMessage.value = error instanceof Error ? error.message : 'Delete failed';
  } finally {
    saving.value = false;
  }
}

function onSmtpPortChange(): void {
  if (Number(form.smtp_port) === 465) {
    form.smtp_ssl = true;
    form.smtp_starttls = false;
  }
}

onMounted(() => {
  blankForm();
  void reload();
});
</script>

<template>
  <div class="email-settings-panel">
    <p
      class="settings-feedback-banner settings-feedback-banner--inline"
      :class="{
        'settings-feedback-banner--error': actionTone === 'error',
        'settings-feedback-banner--ok': actionTone === 'ok',
        'settings-feedback-banner--pending': actionTone === 'pending',
      }"
      role="status"
      aria-live="polite"
    >
      {{ actionMessage || 'Configure inbound mail for Attention, Brain Galaxy, and IDE handoff.' }}
    </p>

    <section class="operator-settings-form__section">
      <header class="operator-settings-form__section-header">
        <h2>Ingest mode</h2>
        <p>
          Prefer live Signal bridge when :7734 is healthy. Stub messages keep the pipe demonstrable offline.
          Passwords stay in Vault — never in settings JSON.
        </p>
      </header>

      <div v-if="snapshot" class="email-settings-panel__toggles">
        <label class="email-settings-panel__toggle">
          <input v-model="snapshot.settings.bridge_enabled" type="checkbox" @change="saveBridgePrefs" />
          <span>Enable Axon Signal email bridge (:7734)</span>
        </label>
        <label class="email-settings-panel__field">
          <span>Bridge workspace id (axon-local project id)</span>
          <input
            v-model="snapshot.settings.bridge_workspace_id"
            type="text"
            @change="saveBridgePrefs"
          />
        </label>
        <label class="email-settings-panel__toggle">
          <input v-model="snapshot.settings.stub_enabled" type="checkbox" @change="saveBridgePrefs" />
          <span>Allow stub triage messages when bridge is offline</span>
        </label>
      </div>

      <dl v-if="auth" class="operator-settings-form__status-grid">
        <div>
          <dt>Mailboxes</dt>
          <dd>{{ auth.account_count }}</dd>
        </div>
        <div>
          <dt>Vault</dt>
          <dd>{{ auth.locked ? 'Locked — unlock for password ops' : 'Unlocked' }}</dd>
        </div>
        <div>
          <dt>Bridge</dt>
          <dd>{{ auth.bridge_enabled ? 'Enabled' : 'Off' }}</dd>
        </div>
      </dl>

      <div class="email-settings-panel__links">
        <button type="button" class="settings-surface__link-button" @click="navigateToAppSurface('vault')">
          Open Vault →
        </button>
        <button type="button" class="settings-surface__link-button" @click="reload">
          Refresh status
        </button>
      </div>
    </section>

    <section class="operator-settings-form__section">
      <header class="operator-settings-form__section-header">
        <h2>Configured mailboxes</h2>
        <p>Per-workspace IMAP/SMTP — enhanced from Axon Signal with folder + remove.</p>
      </header>

      <p v-if="!accounts.length" class="region-copy">
        No mailbox linked yet. Add one below so Attention and Brain Galaxy can surface email follow-ups.
      </p>

      <ul v-else class="email-settings-panel__accounts">
        <li v-for="account in accounts" :key="account.account_id" class="email-settings-panel__account">
          <div>
            <strong>{{ account.email_address }}</strong>
            <p>
              {{ account.workspace_id }} · {{ account.imap.host || '?' }} →
              {{ account.imap.folder }} · poll {{ account.monitor.poll_seconds }}s
            </p>
          </div>
          <div class="email-settings-panel__account-actions">
            <button type="button" @click="prefill(account)">Edit</button>
            <button
              type="button"
              :disabled="testingKey === account.account_id"
              @click="runTest(account.account_id)"
            >
              {{ testingKey === account.account_id ? 'Testing…' : 'Test' }}
            </button>
            <button type="button" :disabled="saving" @click="removeAccount(account.account_id)">
              Remove
            </button>
          </div>
        </li>
      </ul>
    </section>

    <section class="operator-settings-form__section">
      <header class="operator-settings-form__section-header">
        <h2>{{ form.account_id ? 'Edit mailbox' : 'Add mailbox' }}</h2>
        <p>Same shape as Axon Signal Workspace Fabric, with IMAP folder exposed.</p>
      </header>

      <div class="email-settings-panel__form">
        <label>
          <span>Workspace</span>
          <select v-model="form.workspace_id">
            <option value="">Select workspace…</option>
            <option
              v-for="workspace in workspaces"
              :key="workspace.workspace_id"
              :value="workspace.workspace_id"
            >
              {{ workspace.display_name || workspace.workspace_id }}
            </option>
          </select>
        </label>
        <label>
          <span>Email address</span>
          <input v-model="form.email_address" type="email" autocomplete="off" />
        </label>
        <label>
          <span>Display label</span>
          <input v-model="form.display_name" type="text" />
        </label>

        <h3>IMAP</h3>
        <label>
          <span>Host</span>
          <input v-model="form.imap_host" type="text" placeholder="imap.example.com" />
        </label>
        <label>
          <span>Port</span>
          <input v-model.number="form.imap_port" type="number" min="1" max="65535" />
        </label>
        <label>
          <span>Username</span>
          <input v-model="form.imap_username" type="text" placeholder="defaults to email" />
        </label>
        <label>
          <span>Folder</span>
          <input v-model="form.imap_folder" type="text" placeholder="INBOX" />
        </label>
        <label class="email-settings-panel__toggle">
          <input v-model="form.imap_ssl" type="checkbox" />
          <span>SSL</span>
        </label>
        <label>
          <span>IMAP password</span>
          <input v-model="form.password_imap" type="password" autocomplete="new-password" />
        </label>

        <h3>SMTP</h3>
        <label>
          <span>Host</span>
          <input v-model="form.smtp_host" type="text" placeholder="smtp.example.com" />
        </label>
        <label>
          <span>Port</span>
          <input
            v-model.number="form.smtp_port"
            type="number"
            min="1"
            max="65535"
            @change="onSmtpPortChange"
          />
        </label>
        <label>
          <span>Username</span>
          <input v-model="form.smtp_username" type="text" />
        </label>
        <label class="email-settings-panel__toggle">
          <input v-model="form.smtp_ssl" type="checkbox" />
          <span>SSL (465)</span>
        </label>
        <label class="email-settings-panel__toggle">
          <input v-model="form.smtp_starttls" type="checkbox" :disabled="form.smtp_port === 465" />
          <span>STARTTLS (587)</span>
        </label>
        <label>
          <span>SMTP password (optional if same as IMAP)</span>
          <input v-model="form.password_smtp" type="password" autocomplete="new-password" />
        </label>

        <h3>Monitor</h3>
        <label class="email-settings-panel__toggle">
          <input v-model="form.monitor_enabled" type="checkbox" />
          <span>Enable monitor poll</span>
        </label>
        <label>
          <span>Poll interval (seconds)</span>
          <input v-model.number="form.poll_seconds" type="number" min="15" max="3600" />
        </label>

        <div class="email-settings-panel__form-actions">
          <button type="button" class="settings-surface__primary" :disabled="saving" @click="saveMailbox">
            {{ saving ? 'Saving…' : 'Save mailbox' }}
          </button>
          <button type="button" @click="blankForm(form.workspace_id)">Clear form</button>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { useEmailSettingsMailbox } from './useEmailSettingsMailbox';

const {
  snapshot,
  actionMessage,
  actionTone,
  saving,
  testingKey,
  form,
  workspaces,
  accounts,
  auth,
  vaultLocked,
  canSaveMailbox,
  saveButtonLabel,
  blankForm,
  prefill,
  accountHasSecrets,
  reload,
  saveBridgePrefs,
  saveMailbox,
  runTest,
  removeAccount,
  onSmtpPortChange,
  openAxonXVault,
} = useEmailSettingsMailbox();
</script>
<template>
  <div class="email-settings-panel">
    <p
      class="settings-feedback-banner settings-feedback-banner--inline"
      :class="{
        'settings-feedback-banner--error': actionTone === 'error',
        'settings-feedback-banner--ok': actionTone === 'ok',
        'settings-feedback-banner--pending': actionTone === 'pending',
        'settings-feedback-banner--warn': actionTone === 'warn',
      }"
      role="status"
      aria-live="polite"
    >
      {{ actionMessage || 'Configure inbound mail for Attention, Brain Galaxy, and IDE handoff.' }}
    </p>

    <section
      class="email-settings-panel__vault-callout"
      :class="{ 'email-settings-panel__vault-callout--locked': vaultLocked }"
    >
      <div>
        <p class="email-settings-panel__vault-title">Which Vault?</p>
        <p class="email-settings-panel__vault-copy">
          Use the <strong>Axon-X Vault</strong> from this console (top bar
          <strong>VAULT</strong> or the button below) — the same vault for monitor keys and mailbox
          passwords. This is <em>not</em> Thunderbird, cPanel, or the old Axon Signal (:7734)
          settings vault. Mailboxes you saved only in Signal do not appear here unless you turn on
          the bridge below.
        </p>
      </div>
      <div class="email-settings-panel__vault-actions">
        <button type="button" class="settings-surface__primary" @click="openAxonXVault">
          {{ vaultLocked ? 'Unlock Axon-X Vault →' : 'Open Axon-X Vault →' }}
        </button>
        <button type="button" @click="reload">Refresh status</button>
      </div>
      <p class="email-settings-panel__vault-status">
        Status:
        <strong>{{ vaultLocked ? 'Locked' : 'Unlocked' }}</strong>
        · Mailboxes here: <strong>{{ auth?.account_count ?? 0 }}</strong>
      </p>
    </section>

    <section class="operator-settings-form__section">
      <header class="operator-settings-form__section-header">
        <h2>Ingest mode</h2>
        <p>
          Axon-X polls IMAP mailboxes with Vault passwords. Optional :7734 bridge; stubs only when
          no live credentials are available.
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
          <dt>Mailboxes in Axon-X</dt>
          <dd>{{ auth.account_count }}</dd>
        </div>
        <div>
          <dt>Axon-X Vault</dt>
          <dd>{{ auth.locked ? 'Locked' : 'Unlocked' }}</dd>
        </div>
        <div>
          <dt>Signal bridge</dt>
          <dd>{{ auth.bridge_enabled ? 'Enabled' : 'Off' }}</dd>
        </div>
      </dl>
    </section>

    <section class="operator-settings-form__section">
      <header class="operator-settings-form__section-header">
        <h2>Configured mailboxes</h2>
        <p>Saved in Axon-X for this console. One or more per workspace.</p>
      </header>

      <p v-if="!accounts.length" class="region-copy">
        None saved yet in Axon-X. Fill the form below (IMAP host + email), then Save. You can save
        hosts now and add passwords after unlocking Vault.
      </p>

      <ul v-else class="email-settings-panel__accounts">
        <li v-for="account in accounts" :key="account.account_id" class="email-settings-panel__account">
          <div>
            <strong>{{ account.email_address }}</strong>
            <p>
              {{ account.workspace_id }} · {{ account.imap.host || '?' }} →
              {{ account.imap.folder }} · poll {{ account.monitor.poll_seconds }}s ·
              {{ accountHasSecrets(account) ? 'passwords in Vault' : 'no passwords yet' }}
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
        <p>
          Minimum to appear in the list: workspace, email, IMAP host. Passwords need Axon-X Vault
          unlocked.
        </p>
      </header>

      <p
        v-if="vaultLocked"
        class="email-settings-panel__inline-hint email-settings-panel__inline-hint--warn"
      >
        Vault is locked. You can still save this mailbox’s hosts/settings. Passwords will be skipped
        until you unlock Axon-X Vault and save again.
      </p>

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
          <span>Host (required)</span>
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
          <span>IMAP password {{ vaultLocked ? '(needs Vault unlock)' : '' }}</span>
          <input
            v-model="form.password_imap"
            type="password"
            autocomplete="new-password"
            :placeholder="vaultLocked ? 'Unlock Axon-X Vault first' : ''"
          />
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
          <button
            type="button"
            class="settings-surface__primary"
            :disabled="saving || !canSaveMailbox"
            @click="saveMailbox"
          >
            {{ saveButtonLabel }}
          </button>
          <button type="button" @click="blankForm(form.workspace_id)">Clear form</button>
        </div>
      </div>
    </section>
  </div>
</template>

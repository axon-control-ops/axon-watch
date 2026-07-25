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

export function useEmailSettingsMailbox() {
  const shell = useShellStore();
  const snapshot = ref<EmailSettingsSnapshot | null>(null);
  const actionMessage = ref<string | null>(null);
  const actionTone = ref<'idle' | 'ok' | 'error' | 'pending' | 'warn'>('idle');
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
  const vaultLocked = computed(() => Boolean(auth.value?.locked));
  const hasPasswordDraft = computed(
    () => Boolean(form.password_imap.trim() || form.password_smtp.trim()),
  );
  const canSaveMailbox = computed(
    () => Boolean(form.workspace_id.trim() && form.email_address.trim() && form.imap_host.trim()),
  );
  const saveButtonLabel = computed(() => {
    if (saving.value) {
      return 'Saving…';
    }
    if (vaultLocked.value && hasPasswordDraft.value) {
      return 'Save mailbox (passwords skipped until Vault unlock)';
    }
    return form.account_id ? 'Update mailbox' : 'Save mailbox';
  });

  function blankForm(workspaceId?: string): void {
    form.account_id = '';
    form.workspace_id =
      workspaceId || shell.currentWorkspace?.workspace_id || workspaces.value[0]?.workspace_id || '';
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

  function accountHasSecrets(account: EmailMailboxAccount): boolean {
    return Boolean(account.imap.password_ref || account.smtp.password_ref);
  }

  async function reload(): Promise<void> {
    actionTone.value = 'pending';
    actionMessage.value = 'Loading email settings…';
    try {
      snapshot.value = await fetchEmailSettings();
      actionTone.value = 'ok';
      actionMessage.value = snapshot.value.auth.locked
        ? 'Email settings synced. Unlock Axon-X Vault to store mailbox passwords.'
        : 'Email settings synced.';
      if (!form.workspace_id) {
        blankForm();
      }
    } catch (error) {
      actionTone.value = 'error';
      actionMessage.value = error instanceof Error ? error.message : 'Email settings load failed';
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
    if (!canSaveMailbox.value) {
      actionTone.value = 'error';
      actionMessage.value = 'Workspace, email address, and IMAP host are required.';
      return;
    }
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
      if (snapshot.value.account) {
        form.account_id = snapshot.value.account.account_id;
      }
      if (snapshot.value.warning) {
        actionTone.value = 'warn';
        actionMessage.value = snapshot.value.warning;
      } else {
        actionTone.value = 'ok';
        actionMessage.value = `Mailbox saved for ${form.email_address}.`;
      }
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
    const account = accounts.value.find((row) => row.account_id === accountId);
    if (account && !accountHasSecrets(account) && !form.password_imap.trim() && !form.password_smtp.trim()) {
      actionTone.value = 'error';
      actionMessage.value =
        'Test failed: no passwords saved for this mailbox yet. Edit it, enter IMAP password (Vault is unlocked), Save, then Test again.';
      prefill(account);
      return;
    }
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

  function openAxonXVault(): void {
    navigateToAppSurface('vault');
  }

  onMounted(() => {
    blankForm();
    void reload();
  });

  return {
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
  };
}

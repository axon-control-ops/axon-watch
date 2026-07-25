import { onMounted, ref, watch } from 'vue';

import {
  createVaultSecret,
  deleteVaultSecret,
  disableVaultAutoUnlock,
  enableVaultAutoUnlock,
  exportVaultBackup,
  exportVaultCsv,
  fetchVaultSecret,
  fetchVaultSecrets,
  fetchVaultStatus,
  importVaultBackupFile,
  importVaultSecrets,
  lockVault,
  setupVault,
  unlockVault,
  updateVaultSecret,
} from '../api/control-plane';
import { useAppSurface } from './useAppSurface';
import {
  formatVaultFullImportMessage,
  looksLikeAxonVaultCsv,
  parseVaultImportDraft,
  parseVaultImportExport,
  type VaultSecretDetail,
  type VaultSecretRecord,
  type VaultStatusSnapshot,
} from '../lib/vault-surface-view';

export function useVaultSurface() {
  const { appSurface } = useAppSurface();
  const snapshot = ref<VaultStatusSnapshot | null>(null);
  const secrets = ref<VaultSecretRecord[]>([]);
  const loading = ref(false);
  const error = ref('');
  const importDraft = ref('');
  const importFileName = ref('');
  const importBusy = ref(false);
  const importMessage = ref('');
  const importMessageTone = ref<'ok' | 'warn' | 'neutral'>('neutral');

  const setupPassword = ref('');
  const setupConfirmPassword = ref('');
  const setupTotpCode = ref('');
  const setupQrUri = ref('');
  const setupTotpSecret = ref('');

  const unlockPassword = ref('');
  const unlockTotpCode = ref('');
  const rememberMe = ref(false);

  const backupPassword = ref('');
  const backupImportMode = ref<'merge' | 'replace'>('merge');
  const secretDraft = ref({
    name: '',
    category: 'general',
    username: '',
    password: '',
    url: '',
    notes: '',
  });
  const editingSecretId = ref<number | null>(null);
  const revealedSecretId = ref<number | null>(null);
  const revealedDetail = ref<VaultSecretDetail | null>(null);
  const busySecretId = ref<number | null>(null);
  const showAddSecretForm = ref(false);

  async function copySecretValue(value: string, label: string, secretName = ''): Promise<void> {
    const trimmed = value.trim();
    if (!trimmed) {
      importMessage.value = secretName ? `${secretName} has no ${label} to copy.` : `No ${label} to copy.`;
      importMessageTone.value = 'warn';
      return;
    }
    error.value = '';
    try {
      await navigator.clipboard.writeText(trimmed);
      importMessage.value = secretName ? `Copied ${label} for ${secretName}.` : `Copied ${label}.`;
      importMessageTone.value = 'ok';
    } catch (exc) {
      error.value = exc instanceof Error ? exc.message : `Clipboard copy failed for ${label}`;
    }
  }

  function resetSecretDraft(): void {
    secretDraft.value = {
      name: '',
      category: 'general',
      username: '',
      password: '',
      url: '',
      notes: '',
    };
    editingSecretId.value = null;
  }

  function clearReveal(): void {
    revealedSecretId.value = null;
    revealedDetail.value = null;
  }

  async function refresh(): Promise<void> {
    loading.value = true;
    error.value = '';
    try {
      const payload = await fetchVaultStatus();
      snapshot.value = payload.vault;
      if (payload.vault.is_unlocked) {
        secrets.value = await fetchVaultSecrets();
      } else {
        secrets.value = [];
        resetSecretDraft();
        clearReveal();
      }
    } catch (exc) {
      error.value = exc instanceof Error ? exc.message : 'Vault status unavailable';
    } finally {
      loading.value = false;
    }
  }

  async function submitSetup(): Promise<void> {
    error.value = '';
    if (setupPassword.value.length < 8) {
      error.value = 'Master password must be at least 8 characters.';
      return;
    }
    if (setupPassword.value !== setupConfirmPassword.value) {
      error.value = 'Password confirmation does not match.';
      return;
    }
    loading.value = true;
    try {
      const result = await setupVault(setupPassword.value);
      setupTotpSecret.value = result.totp_secret;
      setupQrUri.value = result.qr_data_uri;
      importMessage.value = 'Vault created. Scan the TOTP secret, then confirm with a 2FA code.';
      importMessageTone.value = 'ok';
      await refresh();
    } catch (exc) {
      error.value = exc instanceof Error ? exc.message : 'Vault setup failed';
    } finally {
      loading.value = false;
    }
  }

  async function submitSetupConfirm(): Promise<void> {
    loading.value = true;
    error.value = '';
    try {
      await unlockVault(setupPassword.value, setupTotpCode.value, false);
      setupPassword.value = '';
      setupConfirmPassword.value = '';
      setupTotpCode.value = '';
      setupQrUri.value = '';
      setupTotpSecret.value = '';
      importMessage.value = 'Vault unlocked.';
      importMessageTone.value = 'ok';
      await refresh();
    } catch (exc) {
      error.value = exc instanceof Error ? exc.message : 'Vault confirmation failed';
    } finally {
      loading.value = false;
    }
  }

  async function submitUnlock(): Promise<void> {
    loading.value = true;
    error.value = '';
    try {
      const result = await unlockVault(unlockPassword.value, unlockTotpCode.value, rememberMe.value);
      unlockPassword.value = '';
      unlockTotpCode.value = '';
      importMessage.value = `Vault unlocked (${result.ttl_label}).`;
      importMessageTone.value = 'ok';
      await refresh();
    } catch (exc) {
      error.value = exc instanceof Error ? exc.message : 'Vault unlock failed';
    } finally {
      loading.value = false;
    }
  }

  async function submitLock(): Promise<void> {
    loading.value = true;
    error.value = '';
    try {
      await lockVault();
      clearReveal();
      await refresh();
    } catch (exc) {
      error.value = exc instanceof Error ? exc.message : 'Vault lock failed';
    } finally {
      loading.value = false;
    }
  }

  async function toggleAutoUnlock(enable: boolean): Promise<void> {
    loading.value = true;
    error.value = '';
    try {
      if (enable) {
        await enableVaultAutoUnlock();
        importMessage.value = 'Auto-unlock enabled for this machine.';
      } else {
        await disableVaultAutoUnlock();
        importMessage.value = 'Auto-unlock disabled.';
      }
      importMessageTone.value = 'ok';
      await refresh();
    } catch (exc) {
      error.value = exc instanceof Error ? exc.message : 'Auto-unlock update failed';
    } finally {
      loading.value = false;
    }
  }

  async function saveSecret(): Promise<void> {
    loading.value = true;
    error.value = '';
    try {
      const body = { ...secretDraft.value };
      const wasEditing = editingSecretId.value !== null;
      if (editingSecretId.value) {
        await updateVaultSecret(editingSecretId.value, body);
      } else {
        await createVaultSecret(body);
      }
      const savedName = body.name;
      resetSecretDraft();
      clearReveal();
      showAddSecretForm.value = false;
      await refresh();
      importMessage.value = wasEditing ? `Secret updated: ${savedName}` : `Secret saved: ${savedName}`;
      importMessageTone.value = 'ok';
    } catch (exc) {
      error.value = exc instanceof Error ? exc.message : 'Secret save failed';
    } finally {
      loading.value = false;
    }
  }

  async function removeSecret(secretId: number, secretName = ''): Promise<void> {
    const label = secretName.trim() || `secret ${secretId}`;
    if (!window.confirm(`Delete ${label}? This cannot be undone.`)) {
      return;
    }
    loading.value = true;
    error.value = '';
    try {
      if (editingSecretId.value === secretId) {
        resetSecretDraft();
      }
      if (revealedSecretId.value === secretId) {
        clearReveal();
      }
      await deleteVaultSecret(secretId);
      await refresh();
      importMessage.value = `Deleted ${label}.`;
      importMessageTone.value = 'ok';
    } catch (exc) {
      error.value = exc instanceof Error ? exc.message : 'Secret delete failed';
    } finally {
      loading.value = false;
    }
  }

  async function revealSecret(secretId: number): Promise<void> {
    if (revealedSecretId.value === secretId) {
      clearReveal();
      return;
    }
    busySecretId.value = secretId;
    error.value = '';
    try {
      const detail = await fetchVaultSecret(secretId);
      revealedDetail.value = detail;
      revealedSecretId.value = secretId;
      if (editingSecretId.value !== null) {
        resetSecretDraft();
      }
    } catch (exc) {
      error.value = exc instanceof Error ? exc.message : 'Reveal failed';
    } finally {
      busySecretId.value = null;
    }
  }

  async function startEditSecret(secretId: number): Promise<void> {
    if (editingSecretId.value === secretId) {
      resetSecretDraft();
      return;
    }
    busySecretId.value = secretId;
    error.value = '';
    try {
      const detail = await fetchVaultSecret(secretId);
      clearReveal();
      editingSecretId.value = secretId;
      showAddSecretForm.value = false;
      secretDraft.value = {
        name: detail.name,
        category: detail.category || 'general',
        username: detail.username || '',
        password: detail.password || '',
        url: detail.url || '',
        notes: detail.notes || '',
      };
    } catch (exc) {
      error.value = exc instanceof Error ? exc.message : 'Edit load failed';
    } finally {
      busySecretId.value = null;
    }
  }

  function openAddSecretForm(): void {
    resetSecretDraft();
    clearReveal();
    showAddSecretForm.value = true;
  }

  function closeAddSecretForm(): void {
    showAddSecretForm.value = false;
    if (!editingSecretId.value) {
      resetSecretDraft();
    }
  }

  function toggleAddSecretForm(): void {
    if (showAddSecretForm.value) {
      closeAddSecretForm();
      return;
    }
    openAddSecretForm();
  }

  async function copyRevealedPassword(): Promise<void> {
    if (!revealedDetail.value?.password) {
      return;
    }
    await copySecretValue(revealedDetail.value.password, 'password', revealedDetail.value.name);
  }

  async function copySecretUsername(secret: VaultSecretRecord): Promise<void> {
    await copySecretValue(secret.username || '', 'username', secret.name);
  }

  async function copySecretUrl(secret: VaultSecretRecord): Promise<void> {
    await copySecretValue(secret.url || '', 'URL', secret.name);
  }

  async function exportBackup(): Promise<void> {
    loading.value = true;
    error.value = '';
    try {
      const blob = await exportVaultBackup(backupPassword.value);
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = 'axon-vault-backup.axonvault';
      anchor.click();
      URL.revokeObjectURL(url);
      importMessage.value = 'Encrypted backup downloaded.';
      importMessageTone.value = 'ok';
    } catch (exc) {
      error.value = exc instanceof Error ? exc.message : 'Backup export failed';
    } finally {
      loading.value = false;
    }
  }

  async function exportCsv(format: 'axon' | 'bitwarden'): Promise<void> {
    loading.value = true;
    error.value = '';
    try {
      const blob = await exportVaultCsv(format);
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = `axon-vault-${format}.csv`;
      anchor.click();
      URL.revokeObjectURL(url);
    } catch (exc) {
      error.value = exc instanceof Error ? exc.message : 'CSV export failed';
    } finally {
      loading.value = false;
    }
  }

  async function importBackupFile(file: File): Promise<void> {
    importBusy.value = true;
    error.value = '';
    importMessage.value = '';
    importMessageTone.value = 'neutral';
    try {
      const result = await importVaultBackupFile(file, {
        backupPassword: backupPassword.value,
        mode: backupImportMode.value,
      });
      importMessage.value = formatVaultFullImportMessage(result, file.name);
      const added = Number(result.added ?? 0);
      const updated = Number(result.updated ?? 0);
      const skipped = Number(result.skipped ?? 0);
      importMessageTone.value = added + updated > 0 ? 'ok' : 'warn';
      if (skipped > 0 && backupImportMode.value === 'merge') {
        importMessage.value += ' Use Replace existing names to overwrite skipped rows.';
      }
      await refresh();
    } catch (exc) {
      error.value = exc instanceof Error ? exc.message : 'Backup import failed';
    } finally {
      importBusy.value = false;
    }
  }

  async function importCsvSecrets(text: string, sourceLabel: string): Promise<void> {
    if (!snapshot.value?.is_unlocked) {
      error.value = 'Unlock the vault before importing CSV secrets.';
      return;
    }
    importBusy.value = true;
    error.value = '';
    importMessage.value = '';
    importMessageTone.value = 'neutral';
    try {
      const filename = sourceLabel.toLowerCase().endsWith('.csv') ? sourceLabel : 'vault-import.csv';
      const file = new File([text], filename, { type: 'text/csv' });
      const result = await importVaultBackupFile(file, {
        backupPassword: '',
        mode: backupImportMode.value,
      });
      importMessage.value = formatVaultFullImportMessage(result, sourceLabel);
      const added = Number(result.added ?? 0);
      const updated = Number(result.updated ?? 0);
      const skipped = Number(result.skipped ?? 0);
      importMessageTone.value = added + updated > 0 ? 'ok' : 'warn';
      if (skipped > 0 && backupImportMode.value === 'merge') {
        importMessage.value += ' Use Replace existing names to overwrite skipped rows.';
      }
      importDraft.value = '';
      importFileName.value = '';
      await refresh();
    } catch (exc) {
      error.value = exc instanceof Error ? exc.message : 'CSV import failed';
    } finally {
      importBusy.value = false;
    }
  }

  async function importSecrets(
    secretMap: Record<string, string>,
    sourceLabel: string,
    exportText = '',
  ): Promise<void> {
    importBusy.value = true;
    importMessage.value = '';
    importMessageTone.value = 'neutral';
    error.value = '';
    try {
      if (!exportText && !Object.keys(secretMap).length) {
        importMessage.value = `No importable keys found in ${sourceLabel}.`;
        importMessageTone.value = 'warn';
        return;
      }
      const payload = await importVaultSecrets(secretMap, { exportText });
      snapshot.value = payload.vault;
      if (payload.vault.is_unlocked) {
        secrets.value = await fetchVaultSecrets();
      }
      const imported = payload.vault_import.imported_keys ?? [];
      if (payload.vault_import.count > 0) {
        importMessage.value = `Imported ${payload.vault_import.count} key(s): ${imported.join(', ')}`;
        importMessageTone.value = 'ok';
      } else {
        importMessage.value = `No new monitor keys imported from ${sourceLabel}.`;
        importMessageTone.value = 'warn';
      }
      importDraft.value = '';
      importFileName.value = '';
    } catch (exc) {
      error.value = exc instanceof Error ? exc.message : 'Vault import failed';
    } finally {
      importBusy.value = false;
    }
  }

  async function submitImport(): Promise<void> {
    const draft = importDraft.value;
    if (looksLikeAxonVaultCsv(draft)) {
      await importCsvSecrets(draft, 'pasted CSV');
      return;
    }
    if (draft.trim().startsWith('{')) {
      await importSecrets({}, 'draft', draft);
      return;
    }
    await importSecrets(parseVaultImportDraft(draft), 'draft');
  }

  async function importFromFile(file: File): Promise<void> {
    importFileName.value = file.name;
    const text = await file.text();
    importDraft.value = text;
    const lowerName = file.name.toLowerCase();

    if (snapshot.value?.is_unlocked && (lowerName.endsWith('.axonvault') || lowerName.endsWith('.json'))) {
      await importBackupFile(file);
      return;
    }

    if (looksLikeAxonVaultCsv(text)) {
      await importCsvSecrets(text, file.name);
      return;
    }

    if (lowerName.endsWith('.json') || text.trim().startsWith('{')) {
      await importSecrets({}, file.name, text);
      return;
    }

    await importSecrets(parseVaultImportExport(text, file.name), file.name);
  }

  onMounted(() => {
    void refresh();
  });

  watch(appSurface, (surface) => {
    if (surface === 'vault') {
      void refresh();
    }
  });

  return {
    snapshot,
    secrets,
    loading,
    error,
    importDraft,
    importFileName,
    importBusy,
    importMessage,
    importMessageTone,
    setupPassword,
    setupConfirmPassword,
    setupTotpCode,
    setupQrUri,
    setupTotpSecret,
    unlockPassword,
    unlockTotpCode,
    rememberMe,
    backupPassword,
    backupImportMode,
    secretDraft,
    editingSecretId,
    revealedSecretId,
    revealedDetail,
    busySecretId,
    showAddSecretForm,
    refresh,
    submitSetup,
    submitSetupConfirm,
    submitUnlock,
    submitLock,
    toggleAutoUnlock,
    saveSecret,
    removeSecret,
    revealSecret,
    startEditSecret,
    cancelSecretEdit: resetSecretDraft,
    toggleAddSecretForm,
    openAddSecretForm,
    closeAddSecretForm,
    copyRevealedPassword,
    clearReveal,
    copySecretUsername,
    copySecretUrl,
    exportBackup,
    exportCsv,
    submitImport,
    importFromFile,
    importBackupFile,
  };
}

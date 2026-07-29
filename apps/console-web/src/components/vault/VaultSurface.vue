<script setup lang="ts">
import { computed, nextTick, ref } from 'vue';

import VaultHudPanel from './VaultHudPanel.vue';
import { useVaultSurface } from '../../composables/useVaultSurface';
import {
  formatVaultTimestamp,
  looksLikeAxonVaultCsv,
  vaultConsumerStatusLabel,
  vaultConsumerStatusTone,
  vaultImportFileLabel,
  vaultMissingKeysLabel,
  vaultReadyConsumerCount,
  vaultStateLabel,
  vaultTtlLabel,
} from '../../lib/vault-surface-view';
import {
  vaultConsumerAuthSummary,
  vaultMissingKeysDisplayLabel,
  vaultSubscriptionAccountLabel,
} from '../../lib/runtime-auth-view';

const vault = useVaultSurface();

const snapshot = computed(() => vault.snapshot.value);
const knownKeys = computed(() => snapshot.value?.known_keys ?? []);
const consumers = computed(() => snapshot.value?.consumers ?? []);
const importedKeys = computed(() => snapshot.value?.imported_keys ?? []);
const importedKeyCount = computed(() => snapshot.value?.imported_key_count ?? importedKeys.value.length);
const readyConsumerCount = computed(() => vaultReadyConsumerCount(consumers.value));
const importFileLabel = computed(() => vaultImportFileLabel(snapshot.value?.import_file ?? ''));
const importSubmitLabel = computed(() => {
  const draft = vault.importDraft.value;
  if (looksLikeAxonVaultCsv(draft)) {
    return 'Import CSV secrets';
  }
  if (draft.trim().startsWith('{')) {
    return 'Import JSON monitor keys';
  }
  return 'Import monitor keys';
});
const stateLabel = computed(() =>
  vaultStateLabel(snapshot.value, {
    unavailable: Boolean(vault.error.value) && !snapshot.value,
  }),
);
const ttlLabel = computed(() => vaultTtlLabel(snapshot.value?.ttl_remaining));
const showSetupFlow = computed(
  () =>
    Boolean(vault.setupTotpSecret.value) ||
    Boolean(snapshot.value && snapshot.value.is_setup === false),
);
const showUnlockFlow = computed(
  () => Boolean(snapshot.value?.is_setup) && !snapshot.value?.is_unlocked && !vault.setupTotpSecret.value,
);
const secretSearch = ref('');
const secretCategoryFilter = ref('all');
const secretsExpanded = ref(true);
const defaultCategories = ['general', 'runtime', 'monitor', 'analytics', 'security', 'integration'];
const secretCategoryOptions = computed(() => {
  const values = new Set(defaultCategories);
  for (const secret of vault.secrets.value) {
    if (secret.category) {
      values.add(secret.category);
    }
  }
  if (vault.secretDraft.value.category) {
    values.add(vault.secretDraft.value.category);
  }
  return Array.from(values).sort((left, right) => {
    if (left === 'general') {
      return -1;
    }
    if (right === 'general') {
      return 1;
    }
    return left.localeCompare(right);
  });
});
const filteredSecrets = computed(() => {
  const search = secretSearch.value.trim().toLowerCase();
  const category = secretCategoryFilter.value;
  return vault.secrets.value.filter((secret) => {
    if (category !== 'all' && secret.category !== category) {
      return false;
    }
    if (!search) {
      return true;
    }
    return [
      secret.name,
      secret.category,
      secret.username,
      secret.url,
      secret.notes_preview,
    ].some((value) => value.toLowerCase().includes(search));
  });
});
const hasActiveFilters = computed(() => secretCategoryFilter.value !== 'all' || Boolean(secretSearch.value.trim()));

function clearSecretFilters(): void {
  secretSearch.value = '';
  secretCategoryFilter.value = 'all';
}

function toggleSecretsSection(): void {
  secretsExpanded.value = !secretsExpanded.value;
}

function onAddSecretClick(): void {
  secretsExpanded.value = true;
  vault.toggleAddSecretForm();
}

function scrollSecretRow(secretId: number): void {
  void nextTick(() => {
    document.getElementById(`vault-secret-row-${secretId}`)?.scrollIntoView({
      behavior: 'smooth',
      block: 'nearest',
    });
  });
}

async function onRevealSecret(secretId: number): Promise<void> {
  await vault.revealSecret(secretId);
  if (vault.revealedSecretId.value === secretId) {
    scrollSecretRow(secretId);
  }
}

async function onEditSecret(secretId: number): Promise<void> {
  secretsExpanded.value = true;
  await vault.startEditSecret(secretId);
  if (vault.editingSecretId.value === secretId) {
    scrollSecretRow(secretId);
  }
}

function isSecretBusy(secretId: number): boolean {
  return vault.busySecretId.value === secretId;
}

function onImportFileSelected(event: Event): void {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];
  if (!file) {
    return;
  }
  void vault.importFromFile(file);
  input.value = '';
}

function onBackupFileSelected(event: Event): void {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];
  if (!file) {
    return;
  }
  void vault.importBackupFile(file);
  input.value = '';
}
</script>

<template>
  <main class="region region-center-workbench vault-surface" aria-label="Vault">
    <VaultHudPanel tag="div" panel-class="vault-surface__shell">
      <header class="vault-surface__hero">
        <div class="vault-surface__hero-copy">
          <p class="vault-surface__eyebrow">Operator foundation</p>
          <div class="vault-surface__title-row">
            <h1 class="vault-surface__title">Secure Vault</h1>
            <span class="vault-surface__badge vault-surface__badge--neutral">{{ stateLabel }}</span>
          </div>
          <p class="vault-surface__subtitle">
            AES-256-GCM encrypted secrets with TOTP 2FA. Provider keys and monitor credentials
            resolve locally — values never leave this machine unencrypted.
          </p>
          <div v-if="snapshot" class="vault-surface__stat-row">
            <span class="vault-surface__stat">
              Secrets <strong>{{ vault.secrets.value.length }}</strong>
            </span>
            <span class="vault-surface__stat vault-surface__stat--ok">
              Consumers ready <strong>{{ readyConsumerCount }}/{{ consumers.length }}</strong>
            </span>
            <span v-if="snapshot.is_unlocked" class="vault-surface__stat">
              Session <strong>{{ ttlLabel }}</strong>
            </span>
          </div>
        </div>
        <div class="vault-surface__hero-actions">
          <button type="button" class="vault-surface__button" :disabled="vault.loading.value" @click="vault.refresh">
            {{ vault.loading.value ? 'Refreshing…' : 'Refresh' }}
          </button>
          <button
            v-if="snapshot?.is_unlocked"
            type="button"
            class="vault-surface__button"
            @click="vault.submitLock"
          >
            Lock vault
          </button>
        </div>
      </header>

      <p v-if="vault.error.value" class="vault-surface__error" role="alert">{{ vault.error.value }}</p>
      <p v-else-if="vault.loading.value && !snapshot" class="vault-surface__loading">Loading vault status…</p>

      <VaultHudPanel v-if="showSetupFlow" panel-class="vault-surface__panel vault-surface__panel--full">
        <h2 class="vault-surface__panel-title">First-time setup</h2>
        <p class="vault-surface__hint">Choose a master password (min 8 chars). You will receive a TOTP secret for 2FA.</p>
        <div class="vault-surface__form-grid">
          <label>
            Master password
            <input v-model="vault.setupPassword.value" class="vault-surface__input" type="password" autocomplete="new-password" />
          </label>
          <label>
            Confirm password
            <input v-model="vault.setupConfirmPassword.value" class="vault-surface__input" type="password" autocomplete="new-password" />
          </label>
        </div>
        <button type="button" class="vault-surface__button vault-surface__button--primary" @click="vault.submitSetup">
          Create vault
        </button>
        <div v-if="vault.setupTotpSecret.value" class="vault-surface__setup-confirm">
          <p class="vault-surface__hint">TOTP secret: <span class="vault-surface__mono">{{ vault.setupTotpSecret.value }}</span></p>
          <img v-if="vault.setupQrUri.value" :src="vault.setupQrUri.value" alt="TOTP QR code" class="vault-surface__qr" />
          <label>
            Confirm 2FA code
            <input v-model="vault.setupTotpCode.value" class="vault-surface__input" inputmode="numeric" autocomplete="one-time-code" />
          </label>
          <button type="button" class="vault-surface__button vault-surface__button--primary" @click="vault.submitSetupConfirm">
            Confirm and unlock
          </button>
        </div>
      </VaultHudPanel>

      <VaultHudPanel v-else-if="showUnlockFlow" panel-class="vault-surface__panel vault-surface__panel--full">
        <h2 class="vault-surface__panel-title">Unlock vault</h2>
        <div class="vault-surface__form-grid">
          <label>
            Master password
            <input v-model="vault.unlockPassword.value" class="vault-surface__input" type="password" autocomplete="current-password" />
          </label>
          <label>
            2FA code
            <input v-model="vault.unlockTotpCode.value" class="vault-surface__input" inputmode="numeric" autocomplete="one-time-code" />
          </label>
        </div>
        <label class="vault-surface__checkbox">
          <input v-model="vault.rememberMe.value" type="checkbox" />
          Remember this device (24h session)
        </label>
        <button type="button" class="vault-surface__button vault-surface__button--primary" @click="vault.submitUnlock">
          Unlock
        </button>
        <p v-if="snapshot?.auto_unlock_enabled" class="vault-surface__hint">Auto-unlock keyfile is enabled on this machine.</p>
      </VaultHudPanel>

      <div v-if="snapshot && snapshot.is_unlocked" class="vault-surface__body">
        <aside class="vault-surface__column vault-surface__column--rail">
          <VaultHudPanel panel-class="vault-surface__panel">
            <h2 class="vault-surface__panel-title">Session</h2>
            <dl class="vault-surface__meta">
              <div><dt>State</dt><dd>{{ stateLabel }}</dd></div>
              <div><dt>TTL</dt><dd>{{ ttlLabel }}</dd></div>
              <div><dt>Auto-unlock</dt><dd>{{ snapshot.auto_unlock_enabled ? 'Enabled' : 'Disabled' }}</dd></div>
            </dl>
            <div class="vault-surface__actions">
              <button type="button" class="vault-surface__button" @click="vault.toggleAutoUnlock(true)">Enable auto-unlock</button>
              <button type="button" class="vault-surface__button" @click="vault.toggleAutoUnlock(false)">Disable auto-unlock</button>
            </div>
          </VaultHudPanel>

          <VaultHudPanel panel-class="vault-surface__panel">
            <h2 class="vault-surface__panel-title">Monitor posture</h2>
            <dl class="vault-surface__meta">
              <div><dt>Legacy import file</dt><dd>{{ snapshot.import_file_present ? importFileLabel : 'None' }}</dd></div>
              <div><dt>Resolved keys</dt><dd>{{ snapshot.available_keys.length }}</dd></div>
            </dl>
          </VaultHudPanel>
        </aside>

        <section class="vault-surface__column vault-surface__column--main">
          <div class="vault-surface__secrets-toolbar">
            <button
              type="button"
              class="vault-surface__button vault-surface__button--primary"
              @click="onAddSecretClick"
            >
              {{ vault.showAddSecretForm.value ? 'Close add form' : 'Add secret' }}
            </button>
          </div>

          <div
            v-if="vault.showAddSecretForm.value && !vault.editingSecretId.value"
            class="vault-surface__add-form vault-surface__add-form--floating"
          >
            <div class="vault-surface__form-grid">
              <label>Name<input v-model="vault.secretDraft.value.name" class="vault-surface__input" /></label>
              <label>
                Category
                <select v-model="vault.secretDraft.value.category" class="vault-surface__input">
                  <option v-for="category in secretCategoryOptions" :key="category" :value="category">
                    {{ category }}
                  </option>
                </select>
              </label>
              <label>Username<input v-model="vault.secretDraft.value.username" class="vault-surface__input" /></label>
              <label>Password<input v-model="vault.secretDraft.value.password" class="vault-surface__input" type="password" /></label>
              <label>URL<input v-model="vault.secretDraft.value.url" class="vault-surface__input" /></label>
            </div>
            <label>Notes<textarea v-model="vault.secretDraft.value.notes" class="vault-surface__textarea" rows="3" /></label>
            <div class="vault-surface__actions vault-surface__actions--row">
              <button type="button" class="vault-surface__button vault-surface__button--primary" @click="vault.saveSecret">
                Save secret
              </button>
            </div>
          </div>

          <VaultHudPanel panel-class="vault-surface__panel vault-surface__panel--secrets">
            <button
              type="button"
              class="vault-surface__section-toggle"
              :aria-expanded="secretsExpanded"
              @click="toggleSecretsSection"
            >
              <span class="vault-surface__section-toggle-label">
                <span class="vault-surface__panel-title">Secrets</span>
                <span class="vault-surface__section-toggle-count">{{ vault.secrets.value.length }}</span>
              </span>
              <span class="vault-surface__section-toggle-chevron" aria-hidden="true">
                {{ secretsExpanded ? '▴' : '▾' }}
              </span>
            </button>

            <div v-show="secretsExpanded" class="vault-surface__secrets-body">
            <div v-if="vault.secrets.value.length" class="vault-surface__toolbar">
              <input
                v-model="secretSearch"
                class="vault-surface__input vault-surface__input--compact"
                type="search"
                placeholder="Search name, username, URL, notes"
              />
              <select v-model="secretCategoryFilter" class="vault-surface__input vault-surface__input--compact">
                <option value="all">All categories</option>
                <option v-for="category in secretCategoryOptions" :key="category" :value="category">
                  {{ category }}
                </option>
              </select>
              <button
                v-if="hasActiveFilters"
                type="button"
                class="vault-surface__button"
                @click="clearSecretFilters"
              >
                Clear filters
              </button>
            </div>
            <p v-if="vault.secrets.value.length" class="vault-surface__hint">
              Showing {{ filteredSecrets.length }} of {{ vault.secrets.value.length }} secret(s).
            </p>
            <ul v-if="filteredSecrets.length" class="vault-surface__key-list">
              <li
                v-for="secret in filteredSecrets"
                :id="`vault-secret-row-${secret.id}`"
                :key="secret.id"
                class="vault-surface__key-row"
                :class="{
                  'vault-surface__key-row--active':
                    vault.editingSecretId.value === secret.id || vault.revealedSecretId.value === secret.id,
                }"
              >
                <div class="vault-surface__key-row-main">
                  <div class="vault-surface__key-copy">
                    <span class="vault-surface__key-name">{{ secret.name }}</span>
                    <span class="vault-surface__consumer-meta">
                      {{ secret.category }} · {{ secret.username || 'no username' }} · {{ secret.url || 'no url' }}
                    </span>
                    <span class="vault-surface__key-meta">Updated {{ formatVaultTimestamp(secret.updated_at) }}</span>
                    <p v-if="secret.notes_preview" class="vault-surface__key-notes">{{ secret.notes_preview }}</p>
                  </div>
                  <div class="vault-surface__actions">
                    <button
                      type="button"
                      class="vault-surface__button"
                      :disabled="isSecretBusy(secret.id)"
                      @click="onEditSecret(secret.id)"
                    >
                      {{ vault.editingSecretId.value === secret.id ? 'Close edit' : 'Edit' }}
                    </button>
                    <button
                      v-if="secret.username"
                      type="button"
                      class="vault-surface__button"
                      @click="vault.copySecretUsername(secret)"
                    >
                      Copy user
                    </button>
                    <button
                      v-if="secret.url"
                      type="button"
                      class="vault-surface__button"
                      @click="vault.copySecretUrl(secret)"
                    >
                      Copy URL
                    </button>
                    <button
                      type="button"
                      class="vault-surface__button"
                      :disabled="isSecretBusy(secret.id)"
                      @click="onRevealSecret(secret.id)"
                    >
                      {{
                        isSecretBusy(secret.id)
                          ? 'Loading…'
                          : vault.revealedSecretId.value === secret.id
                            ? 'Hide'
                            : 'Reveal'
                      }}
                    </button>
                    <button type="button" class="vault-surface__button" @click="vault.removeSecret(secret.id, secret.name)">
                      Delete
                    </button>
                  </div>
                </div>

                <div
                  v-if="vault.revealedSecretId.value === secret.id && vault.revealedDetail.value"
                  class="vault-surface__key-reveal"
                >
                  <div class="vault-surface__key-reveal-row">
                    <span class="vault-surface__key-reveal-label">Password</span>
                    <code class="vault-surface__mono vault-surface__key-reveal-value">
                      {{ vault.revealedDetail.value.password || '(empty)' }}
                    </code>
                  </div>
                  <div v-if="vault.revealedDetail.value.notes" class="vault-surface__key-reveal-row">
                    <span class="vault-surface__key-reveal-label">Notes</span>
                    <div class="vault-surface__key-notes">{{ vault.revealedDetail.value.notes }}</div>
                  </div>
                  <div class="vault-surface__actions vault-surface__actions--row">
                    <button
                      v-if="vault.revealedDetail.value.password"
                      type="button"
                      class="vault-surface__button"
                      @click="vault.copyRevealedPassword"
                    >
                      Copy password
                    </button>
                    <button type="button" class="vault-surface__button" @click="vault.clearReveal">Hide</button>
                  </div>
                </div>

                <div v-if="vault.editingSecretId.value === secret.id" class="vault-surface__key-edit">
                  <div class="vault-surface__form-grid">
                    <label>Name<input v-model="vault.secretDraft.value.name" class="vault-surface__input" /></label>
                    <label>
                      Category
                      <select v-model="vault.secretDraft.value.category" class="vault-surface__input">
                        <option v-for="category in secretCategoryOptions" :key="category" :value="category">
                          {{ category }}
                        </option>
                      </select>
                    </label>
                    <label>Username<input v-model="vault.secretDraft.value.username" class="vault-surface__input" /></label>
                    <label>Password<input v-model="vault.secretDraft.value.password" class="vault-surface__input" type="password" /></label>
                    <label>URL<input v-model="vault.secretDraft.value.url" class="vault-surface__input" /></label>
                  </div>
                  <label>Notes<textarea v-model="vault.secretDraft.value.notes" class="vault-surface__textarea" rows="4" /></label>
                  <div class="vault-surface__actions vault-surface__actions--row">
                    <button type="button" class="vault-surface__button vault-surface__button--primary" @click="vault.saveSecret">
                      Update secret
                    </button>
                    <button type="button" class="vault-surface__button" @click="vault.cancelSecretEdit">Cancel</button>
                  </div>
                </div>
              </li>
            </ul>
            <p v-else-if="vault.secrets.value.length" class="vault-surface__empty">No secrets match the current filters.</p>
            <p v-else class="vault-surface__empty">No secrets stored yet.</p>
            </div>
          </VaultHudPanel>

          <VaultHudPanel panel-class="vault-surface__panel">
            <h2 class="vault-surface__panel-title">Consumer readiness</h2>
            <ul v-if="consumers.length" class="vault-surface__consumer-list">
              <li v-for="consumer in consumers" :key="consumer.id" class="vault-surface__consumer">
                <div class="vault-surface__consumer-head">
                  <strong>{{ consumer.label }}</strong>
                  <span class="vault-surface__badge" :class="`vault-surface__badge--${vaultConsumerStatusTone(consumer.status)}`">
                    {{ vaultConsumerStatusLabel(consumer.status) }}
                  </span>
                </div>
                <p v-if="vaultConsumerAuthSummary(consumer)" class="vault-surface__consumer-meta vault-surface__consumer-meta--ok">
                  {{ vaultConsumerAuthSummary(consumer) }}
                </p>
                <p v-else-if="consumer.auth_note" class="vault-surface__consumer-meta">
                  {{ consumer.auth_note }}
                </p>
                <p
                  v-if="consumer.missing_keys.length && consumer.status !== 'ready'"
                  class="vault-surface__consumer-meta vault-surface__consumer-meta--warn"
                >
                  Needs: {{ vaultMissingKeysDisplayLabel(consumer) }}
                </p>
                <p
                  v-else-if="consumer.missing_keys.length && vaultSubscriptionAccountLabel(consumer)"
                  class="vault-surface__consumer-meta"
                >
                  Optional vault key: {{ vaultMissingKeysLabel(consumer) }}
                </p>
              </li>
            </ul>
          </VaultHudPanel>
        </section>

        <aside class="vault-surface__column vault-surface__column--import">
          <VaultHudPanel panel-class="vault-surface__panel">
            <h2 class="vault-surface__panel-title">Backup export</h2>
            <label>Backup password<input v-model="vault.backupPassword.value" class="vault-surface__input" type="password" /></label>
            <div class="vault-surface__actions">
              <button type="button" class="vault-surface__button" @click="vault.exportBackup">Encrypted backup</button>
              <button type="button" class="vault-surface__button" @click="vault.exportCsv('axon')">CSV (Axon)</button>
              <button type="button" class="vault-surface__button" @click="vault.exportCsv('bitwarden')">CSV (Bitwarden)</button>
            </div>
          </VaultHudPanel>

          <VaultHudPanel panel-class="vault-surface__panel">
            <h2 class="vault-surface__panel-title">Import</h2>
            <label class="vault-surface__file-label">
              <span class="vault-surface__file-button">Backup / CSV / monitor file</span>
              <input class="vault-surface__file-input" type="file" accept=".csv,.json,.axonvault" @change="onImportFileSelected" />
            </label>
            <label class="vault-surface__file-label">
              <span class="vault-surface__file-button">Encrypted backup only</span>
              <input class="vault-surface__file-input" type="file" accept=".axonvault,.json" @change="onBackupFileSelected" />
            </label>
            <select v-model="vault.backupImportMode.value" class="vault-surface__input">
              <option value="merge">Merge import (skip existing names)</option>
              <option value="replace">Replace existing names</option>
            </select>
            <textarea v-model="vault.importDraft.value" class="vault-surface__textarea" rows="6" placeholder="Axon CSV (name,category,username,password…) or monitor KEY=value lines" />
            <button type="button" class="vault-surface__button vault-surface__button--primary" :disabled="vault.importBusy.value" @click="vault.submitImport">
              {{ importSubmitLabel }}
            </button>
            <p
              v-if="vault.importMessage.value"
              class="vault-surface__message"
              :class="{
                'vault-surface__message--ok': vault.importMessageTone.value === 'ok',
                'vault-surface__message--warn': vault.importMessageTone.value === 'warn',
              }"
            >
              {{ vault.importMessage.value }}
            </p>
            <p class="vault-surface__hint">Axon CSV imports every secret row. Monitor allowlist (KEY=value only): <span class="vault-surface__mono">{{ knownKeys.join(', ') }}</span></p>
          </VaultHudPanel>
        </aside>
      </div>
    </VaultHudPanel>
  </main>
</template>

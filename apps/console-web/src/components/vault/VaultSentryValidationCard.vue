<script setup lang="ts">
import { computed, ref } from 'vue';

import { validateVaultSentry } from '../../api/control-plane';
import {
  formatVaultTimestamp,
  type VaultSentryValidation,
} from '../../lib/vault-surface-view';

const validation = ref<VaultSentryValidation | null>(null);
const busy = ref(false);
const error = ref('');

const validationTone = computed(() => {
  if (!validation.value) {
    return 'neutral';
  }
  return validation.value.ok ? 'ok' : 'critical';
});

const validationLabel = computed(() => {
  if (!validation.value) {
    return 'Not checked';
  }
  return validation.value.ok ? 'Validated' : 'Needs attention';
});

async function validate(): Promise<void> {
  busy.value = true;
  error.value = '';
  try {
    validation.value = await validateVaultSentry();
  } catch (exc) {
    error.value = exc instanceof Error ? exc.message : 'Sentry validation failed';
  } finally {
    busy.value = false;
  }
}
</script>

<template>
  <div class="vault-sentry-validation">
    <div class="vault-surface__consumer-head">
      <strong>Sentry token health</strong>
      <span class="vault-surface__badge" :class="`vault-surface__badge--${validationTone}`">
        {{ validationLabel }}
      </span>
    </div>
    <p class="vault-surface__hint">
      Checks Vault keys against Sentry read access, project visibility, and write-scope probe.
    </p>
    <button
      type="button"
      class="vault-surface__button vault-sentry-validation__button"
      :disabled="busy"
      @click="validate"
    >
      {{ busy ? 'Validating…' : 'Validate Sentry' }}
    </button>
    <p v-if="error" class="vault-surface__message vault-surface__message--warn">
      {{ error }}
    </p>
    <dl v-if="validation" class="vault-surface__meta vault-sentry-validation__meta">
      <div>
        <dt>Token</dt>
        <dd>
          {{ validation.token_key || 'missing' }} · {{ validation.token_prefix || 'none' }} ·
          {{ validation.token_length || 0 }} chars
        </dd>
      </div>
      <div>
        <dt>Project</dt>
        <dd>{{ validation.org_slug || 'missing org' }}/{{ validation.project_slug || 'missing project' }}</dd>
      </div>
      <div>
        <dt>Read / Project / Write</dt>
        <dd>
          {{ validation.read_ok ? 'read ok' : 'read failed' }} ·
          {{ validation.project_found ? 'project visible' : 'project missing' }} ·
          {{ validation.write_ok ? 'write ok' : 'write failed' }}
        </dd>
      </div>
      <div>
        <dt>Checked</dt>
        <dd>{{ formatVaultTimestamp(validation.checked_at) }}</dd>
      </div>
    </dl>
    <p v-if="validation?.detail" class="vault-surface__hint">
      {{ validation.detail }}
    </p>
    <p v-if="validation?.write_detail" class="vault-surface__hint">
      Write probe: {{ validation.write_detail }}
    </p>
  </div>
</template>

<style scoped>
.vault-sentry-validation {
  display: grid;
  gap: 0.55rem;
  margin-top: 0.8rem;
  padding-top: 0.75rem;
  border-top: 1px solid rgba(0, 242, 255, 0.1);
}

.vault-sentry-validation :deep(.vault-surface__hint),
.vault-sentry-validation :deep(.vault-surface__message) {
  margin-top: 0;
}

.vault-sentry-validation__button {
  justify-content: center;
  width: 100%;
}

.vault-sentry-validation__meta {
  gap: 0.45rem;
}
</style>

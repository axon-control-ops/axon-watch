<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';

import {
  fetchEmailSettings,
  sendEmailReply,
  type EmailMailboxAccount,
} from '../../api/email-settings-api';
import { useShellStore } from '../../stores/shell';

const emit = defineEmits<{ close: [] }>();

const shell = useShellStore();

const accounts = ref<EmailMailboxAccount[]>([]);
const settingsError = ref('');
const loadingAccounts = ref(true);

const workspaceId = ref(shell.currentWorkspace?.workspace_id ?? '');
const accountId = ref('');
const to = ref('');
const subject = ref('');
const body = ref('');
const approved = ref(false);
const sending = ref(false);
const sentReceipt = ref('');
const sendError = ref('');

const accountsForWorkspace = computed(() =>
  accounts.value.filter((account) => account.workspace_id === workspaceId.value),
);

const selectedAccount = computed(
  () => accountsForWorkspace.value.find((account) => account.account_id === accountId.value) ?? null,
);

watch(workspaceId, () => {
  const first = accountsForWorkspace.value[0];
  accountId.value = first?.account_id ?? '';
});

async function loadAccounts(): Promise<void> {
  loadingAccounts.value = true;
  settingsError.value = '';
  try {
    const snapshot = await fetchEmailSettings();
    accounts.value = snapshot.settings.accounts;
    const first = accountsForWorkspace.value[0];
    accountId.value = first?.account_id ?? '';
  } catch (error) {
    settingsError.value = error instanceof Error ? error.message : 'Failed to load email settings';
    accounts.value = [];
  } finally {
    loadingAccounts.value = false;
  }
}

onMounted(() => {
  void loadAccounts();
});

const canSend = computed(
  () =>
    Boolean(
      selectedAccount.value &&
        to.value.trim() &&
        subject.value.trim() &&
        body.value.trim() &&
        approved.value,
    ) && !sending.value,
);

async function send(): Promise<void> {
  if (!canSend.value || !selectedAccount.value) {
    return;
  }
  sending.value = true;
  sendError.value = '';
  sentReceipt.value = '';
  try {
    const result = await sendEmailReply({
      workspace_id: workspaceId.value,
      account_id: selectedAccount.value.account_id,
      to: to.value.trim(),
      subject: subject.value.trim(),
      body: body.value.trim(),
      confirm_send: true,
    });
    sentReceipt.value = `Sent ${result.message_id} from ${result.from} to ${result.to}`;
    approved.value = false;
  } catch (error) {
    sendError.value = error instanceof Error ? error.message : 'Email send failed';
  } finally {
    sending.value = false;
  }
}

function close(): void {
  emit('close');
}

function onKeydown(event: KeyboardEvent): void {
  if (event.key === 'Escape') {
    close();
  }
}
</script>

<template>
  <Teleport to="body">
    <div
      class="email-compose-modal"
      role="dialog"
      aria-modal="true"
      aria-label="Compose email"
      @keydown="onKeydown"
    >
      <div class="email-compose-modal__scrim" @click="close" />
      <div class="email-compose-modal__panel">
        <header class="email-compose-modal__header">
          <h2 class="email-compose-modal__title">Compose email</h2>
          <button
            type="button"
            class="email-compose-modal__close"
            aria-label="Close compose"
            @click="close"
          >
            ×
          </button>
        </header>

        <p v-if="settingsError" class="email-compose-modal__error" role="alert">{{ settingsError }}</p>

        <div class="email-compose-modal__form">
          <label class="email-compose-modal__field">
            <span>Workspace</span>
            <select v-model="workspaceId">
              <option v-for="ws in shell.workspaces" :key="ws.workspace_id" :value="ws.workspace_id">
                {{ ws.display_name || ws.workspace_id }}
              </option>
            </select>
          </label>

          <label class="email-compose-modal__field">
            <span>Send from</span>
            <select v-model="accountId" :disabled="accountsForWorkspace.length === 0">
              <option v-if="accountsForWorkspace.length === 0" value="">No mailbox configured</option>
              <option
                v-for="account in accountsForWorkspace"
                :key="account.account_id"
                :value="account.account_id"
              >
                {{ account.email_address || account.smtp.from_email }}
              </option>
            </select>
          </label>

          <label class="email-compose-modal__field">
            <span>To</span>
            <input v-model="to" type="text" autocomplete="off" placeholder="recipient@example.com">
          </label>

          <label class="email-compose-modal__field">
            <span>Subject</span>
            <input v-model="subject" type="text" autocomplete="off">
          </label>

          <label class="email-compose-modal__field">
            <span>Body</span>
            <textarea v-model="body" rows="8" />
          </label>

          <label class="email-compose-modal__approval">
            <input v-model="approved" type="checkbox">
            <span>I reviewed this exact message and approve sending it.</span>
          </label>

          <button
            type="button"
            class="email-compose-modal__send"
            :disabled="!canSend"
            @click="send"
          >
            {{ sending ? 'SENDING…' : 'SEND EMAIL' }}
          </button>

          <p
            v-if="!loadingAccounts && !selectedAccount"
            class="email-compose-modal__error"
          >
            Configure a mailbox for this workspace under Settings → Email before composing.
          </p>
          <p v-if="sentReceipt" class="email-compose-modal__receipt">{{ sentReceipt }}</p>
          <p v-if="sendError" class="email-compose-modal__error" role="alert">{{ sendError }}</p>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.email-compose-modal {
  position: fixed;
  inset: 0;
  z-index: 900;
  display: flex;
  align-items: center;
  justify-content: center;
}

.email-compose-modal__scrim {
  position: absolute;
  inset: 0;
  background: rgba(4, 8, 14, 0.6);
}

.email-compose-modal__panel {
  position: relative;
  width: min(520px, 92vw);
  max-height: 88vh;
  overflow-y: auto;
  background: var(--axon-panel-bg, #0b1118);
  border: 1px solid rgba(0, 210, 255, 0.2);
  border-radius: 0.5rem;
  padding: 20px 22px 24px;
  box-shadow: 0 24px 48px rgba(0, 0, 0, 0.45);
}

.email-compose-modal__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
}

.email-compose-modal__title {
  margin: 0;
  font-size: 18px;
  color: var(--text-primary);
}

.email-compose-modal__close {
  border: none;
  background: transparent;
  color: inherit;
  font-size: 22px;
  line-height: 1;
  cursor: pointer;
  opacity: 0.7;
  padding: 4px 8px;
}

.email-compose-modal__close:hover {
  opacity: 1;
}

.email-compose-modal__form {
  display: grid;
  gap: 0.55rem;
}

.email-compose-modal__field {
  display: grid;
  gap: 0.2rem;
  color: var(--text-secondary);
  font-size: 0.65rem;
  text-transform: uppercase;
}

.email-compose-modal__field input,
.email-compose-modal__field select,
.email-compose-modal__field textarea {
  box-sizing: border-box;
  width: 100%;
  border: 1px solid rgba(0, 210, 255, 0.2);
  border-radius: 0.25rem;
  padding: 0.4rem;
  background: rgba(0, 7, 12, 0.88);
  color: var(--text-primary);
  font: inherit;
  line-height: 1.4;
  text-transform: none;
}

.email-compose-modal__field textarea {
  resize: vertical;
}

.email-compose-modal__approval {
  display: flex;
  align-items: flex-start;
  gap: 0.4rem;
  color: var(--text-secondary);
  font-size: 0.7rem;
}

.email-compose-modal__send {
  justify-self: start;
  border: 1px solid rgba(0, 210, 255, 0.34);
  border-radius: 0.25rem;
  padding: 0.4rem 0.75rem;
  background: rgba(0, 120, 160, 0.2);
  color: var(--accent-brand);
  font-size: 0.68rem;
  letter-spacing: 0.08em;
}

.email-compose-modal__send:disabled {
  cursor: not-allowed;
  opacity: 0.45;
}

.email-compose-modal__receipt {
  color: var(--state-healthy);
  font-size: 0.7rem;
}

.email-compose-modal__error {
  color: var(--state-critical);
  font-size: 0.7rem;
}
</style>

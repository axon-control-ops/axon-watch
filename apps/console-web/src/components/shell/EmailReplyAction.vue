<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';

import {
  fetchEmailSettings,
  sendEmailReply,
  suggestEmailReply,
  type EmailMailboxAccount,
} from '../../api/email-settings-api';

const props = defineProps<{
  workspaceId?: string | null;
  meta?: Record<string, unknown> | null;
}>();

const accounts = ref<EmailMailboxAccount[]>([]);
const settingsError = ref('');

const workspaceId = computed(() => String(props.workspaceId || '').trim());
const suggestedSubject = computed(() =>
  String(props.meta?.suggested_reply_subject ?? '').trim(),
);
const suggestedBody = computed(() => String(props.meta?.suggested_reply_body ?? '').trim());
const sourceSubject = computed(() =>
  String(props.meta?.subject ?? props.meta?.email_subject ?? suggestedSubject.value ?? '').trim(),
);
const sourceText = computed(() =>
  String(
    props.meta?.text
      ?? props.meta?.body
      ?? props.meta?.email_body
      ?? props.meta?.snippet
      ?? props.meta?.summary
      ?? suggestedBody.value
      ?? '',
  ).trim(),
);
const recipient = computed(() => String(props.meta?.sender ?? '').trim());
const isEmailSignal = computed(() => props.meta?.signal_family === 'email_triage');

const workspaceAccount = computed(() => {
  const workspace = workspaceId.value;
  if (!workspace) {
    return null;
  }
  return accounts.value.find((account) => account.workspace_id === workspace) ?? null;
});

const accountAddress = computed(
  () => workspaceAccount.value?.email_address
    || workspaceAccount.value?.smtp.from_email
    || '',
);
const operatorName = computed(() => String(workspaceAccount.value?.display_name || '').trim());

const subject = ref('');
const body = ref('');
const approved = ref(false);
const sending = ref(false);
const suggestionLoading = ref(false);
const sentReceipt = ref('');
const sendError = ref('');

async function loadAccounts(): Promise<void> {
  settingsError.value = '';
  try {
    const snapshot = await fetchEmailSettings();
    accounts.value = snapshot.settings.accounts;
  } catch (error) {
    settingsError.value =
      error instanceof Error ? error.message : 'Failed to load email settings';
    accounts.value = [];
  }
}

function applyStoredSuggestion(): void {
  subject.value = suggestedSubject.value;
  body.value = suggestedBody.value;
}

function suggestionKey(): string {
  return [
    sourceSubject.value,
    sourceText.value,
    recipient.value,
    operatorName.value,
  ].join('\u0000');
}

async function refreshSuggestedDraft(): Promise<void> {
  if (!isEmailSignal.value || !recipient.value || !sourceText.value) {
    return;
  }
  const key = suggestionKey();
  suggestionLoading.value = true;
  try {
    const draft = await suggestEmailReply({
      subject: sourceSubject.value || suggestedSubject.value,
      sender: recipient.value,
      text: sourceText.value,
      operator_name: operatorName.value,
    });
    if (key !== suggestionKey()) {
      return;
    }
    subject.value = draft.reply_subject;
    body.value = draft.reply_body;
  } catch (error) {
    if (key === suggestionKey()) {
      sendError.value =
        error instanceof Error ? error.message : 'Email reply suggestion failed';
    }
  } finally {
    if (key === suggestionKey()) {
      suggestionLoading.value = false;
    }
  }
}

watch(
  () => [
    suggestedSubject.value,
    suggestedBody.value,
    sourceSubject.value,
    sourceText.value,
    recipient.value,
    workspaceId.value,
    workspaceAccount.value?.account_id ?? '',
    operatorName.value,
  ],
  () => {
    applyStoredSuggestion();
    approved.value = false;
    sentReceipt.value = '';
    sendError.value = '';
    void refreshSuggestedDraft();
  },
  { immediate: true },
);

onMounted(() => {
  void loadAccounts();
});

const canSend = computed(
  () =>
    Boolean(
      workspaceAccount.value &&
        recipient.value &&
        subject.value.trim() &&
        body.value.trim() &&
        approved.value,
    ) && !sending.value,
);

async function sendApprovedReply(): Promise<void> {
  if (!canSend.value || !workspaceAccount.value) {
    return;
  }
  sending.value = true;
  sendError.value = '';
  sentReceipt.value = '';
  try {
    const result = await sendEmailReply({
      workspace_id: workspaceId.value,
      account_id: workspaceAccount.value.account_id,
      to: recipient.value,
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
</script>

<template>
  <section v-if="isEmailSignal && (suggestedBody || sourceText)" class="email-reply-action">
    <p class="email-reply-action__label">
      Suggested reply · {{ suggestionLoading ? 'regenerating sender-facing draft…' : 'review before sending' }}
    </p>
    <p class="email-reply-action__route">
      {{
        accountAddress
          ? `From ${accountAddress} (${workspaceId || 'workspace'})`
          : 'No mailbox configured for this workspace'
      }}
      · To {{ recipient }}
    </p>
    <label class="email-reply-action__field">
      <span>Subject</span>
      <input v-model="subject" type="text" autocomplete="off">
    </label>
    <label class="email-reply-action__field">
      <span>Reply</span>
      <textarea v-model="body" rows="7" />
    </label>
    <label class="email-reply-action__approval">
      <input v-model="approved" type="checkbox">
      <span>I reviewed this exact message and approve sending it.</span>
    </label>
    <button
      type="button"
      class="email-reply-action__send"
      :disabled="!canSend"
      @click="sendApprovedReply"
    >
      {{ sending ? 'SENDING…' : 'SEND APPROVED REPLY' }}
    </button>
    <p v-if="!workspaceAccount" class="email-reply-action__error">
      Configure this workspace mailbox under Settings → Email
      {{ workspaceId ? `(${workspaceId})` : '' }}.
    </p>
    <p v-if="settingsError" class="email-reply-action__error" role="alert">{{ settingsError }}</p>
    <p v-if="sentReceipt" class="email-reply-action__receipt">{{ sentReceipt }}</p>
    <p v-if="sendError" class="email-reply-action__error" role="alert">{{ sendError }}</p>
  </section>
</template>

<style scoped>
.email-reply-action {
  display: grid;
  gap: 0.45rem;
  margin: 0.55rem 0;
  padding: 0.55rem;
  border: 1px solid rgba(0, 210, 255, 0.2);
  border-radius: 0.35rem;
  background: rgba(0, 12, 20, 0.68);
}

.email-reply-action__label,
.email-reply-action__route,
.email-reply-action__receipt,
.email-reply-action__error {
  margin: 0;
}

.email-reply-action__label {
  color: var(--accent-brand);
  font-size: 0.68rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.email-reply-action__route,
.email-reply-action__approval {
  color: var(--text-secondary);
  font-size: 0.7rem;
}

.email-reply-action__field {
  display: grid;
  gap: 0.2rem;
  color: var(--text-secondary);
  font-size: 0.65rem;
  text-transform: uppercase;
}

.email-reply-action__field input,
.email-reply-action__field textarea {
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

.email-reply-action__field textarea {
  resize: vertical;
}

.email-reply-action__approval {
  display: flex;
  align-items: flex-start;
  gap: 0.4rem;
}

.email-reply-action__send {
  justify-self: start;
  border: 1px solid rgba(0, 210, 255, 0.34);
  border-radius: 0.25rem;
  padding: 0.38rem 0.6rem;
  background: rgba(0, 120, 160, 0.2);
  color: var(--accent-brand);
  font-size: 0.66rem;
  letter-spacing: 0.08em;
}

.email-reply-action__send:disabled {
  cursor: not-allowed;
  opacity: 0.45;
}

.email-reply-action__receipt {
  color: var(--state-healthy);
  font-size: 0.7rem;
}

.email-reply-action__error {
  color: var(--state-critical);
  font-size: 0.7rem;
}
</style>

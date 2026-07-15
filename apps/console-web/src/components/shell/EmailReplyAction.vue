<script setup lang="ts">
import { computed, ref, watch } from 'vue';

import { sendEmailReply } from '../../api/email-settings-api';

const props = defineProps<{
  meta?: Record<string, unknown> | null;
}>();

const accountId = computed(() => String(props.meta?.email_account_id ?? '').trim());
const accountAddress = computed(() => String(props.meta?.email_account_address ?? '').trim());
const suggestedSubject = computed(() =>
  String(props.meta?.suggested_reply_subject ?? '').trim(),
);
const suggestedBody = computed(() => String(props.meta?.suggested_reply_body ?? '').trim());
const recipient = computed(() => String(props.meta?.sender ?? '').trim());
const isEmailSignal = computed(() => props.meta?.signal_family === 'email_triage');

const subject = ref('');
const body = ref('');
const approved = ref(false);
const sending = ref(false);
const sentReceipt = ref('');
const sendError = ref('');

watch(
  () => [
    suggestedSubject.value,
    suggestedBody.value,
    recipient.value,
    accountId.value,
  ],
  () => {
    subject.value = suggestedSubject.value;
    body.value = suggestedBody.value;
    approved.value = false;
    sentReceipt.value = '';
    sendError.value = '';
  },
  { immediate: true },
);

const canSend = computed(
  () =>
    Boolean(
      accountId.value &&
        recipient.value &&
        subject.value.trim() &&
        body.value.trim() &&
        approved.value,
    ) && !sending.value,
);

async function sendApprovedReply(): Promise<void> {
  if (!canSend.value) {
    return;
  }
  sending.value = true;
  sendError.value = '';
  sentReceipt.value = '';
  try {
    const result = await sendEmailReply({
      account_id: accountId.value,
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
  <section v-if="isEmailSignal && suggestedBody" class="email-reply-action">
    <p class="email-reply-action__label">Suggested reply · review before sending</p>
    <p class="email-reply-action__route">
      {{ accountAddress ? `From ${accountAddress}` : 'Sending mailbox unavailable' }}
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
    <p v-if="!accountId" class="email-reply-action__error">
      This signal has no source mailbox receipt. Refresh signals after IMAP reconnects.
    </p>
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

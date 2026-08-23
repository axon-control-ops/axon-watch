<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';

import { useShellStore } from '../../stores/shell';
import type { InboxItem } from '../../contracts/canonical';
import { isEmailSignalRead, markEmailSignalRead } from '../../lib/email-read-state';
import {
  fetchEmailFolders,
  fetchEmailMessages,
  type EmailFolderMessage,
  type EmailFolderRole,
  type EmailFoldersResult,
} from '../../api/inbox-api';
import EmailComposeModal from './EmailComposeModal.vue';

const shell = useShellStore();

const selectedSignalId = ref<string | null>(null);
const composeOpen = ref(false);
const refreshing = ref(false);

// "Inbox" stays the existing fleet-wide triage view (unread tracking,
// suggested replies). The other tabs are a plain, read-only window into
// that one real IMAP folder for the currently selected workspace's mailbox
// -- they are raw mail, not signals, so none of the triage machinery
// (unread dots, suggested replies) applies to them.
const FOLDER_TABS: { role: EmailFolderRole; label: string }[] = [
  { role: 'inbox', label: 'Inbox' },
  { role: 'sent', label: 'Sent' },
  { role: 'junk', label: 'Junk' },
  { role: 'archive', label: 'Archive' },
];
const activeFolder = ref<EmailFolderRole>('inbox');
const availableFolders = ref<EmailFoldersResult['folders']>({});
const folderMessages = ref<EmailFolderMessage[]>([]);
const folderLoading = ref(false);
const folderError = ref<string | null>(null);
const selectedFolderMessageUid = ref<string | null>(null);

const currentWorkspaceId = computed(() => shell.currentWorkspace?.workspace_id ?? '');

async function loadFolderTabAvailability(): Promise<void> {
  if (!currentWorkspaceId.value) {
    availableFolders.value = {};
    return;
  }
  try {
    const result = await fetchEmailFolders(currentWorkspaceId.value);
    availableFolders.value = result.folders;
  } catch {
    // No mailbox configured for this workspace, or watch unreachable --
    // tabs just show as unavailable rather than surfacing a hard error.
    availableFolders.value = {};
  }
}

async function loadFolderMessages(role: EmailFolderRole): Promise<void> {
  if (role === 'inbox' || !currentWorkspaceId.value) {
    return;
  }
  folderLoading.value = true;
  folderError.value = null;
  try {
    // A real live IMAP fetch is uncached per-message (~2-3s per message on
    // shared hosting) -- keep the cold-cache latency tolerable even though
    // the backend now caches this for 60s after the first fetch.
    const result = await fetchEmailMessages(currentWorkspaceId.value, role, { limit: 10 });
    folderMessages.value = result.items;
    selectedFolderMessageUid.value = result.items[0]?.uid ?? null;
  } catch (error) {
    folderMessages.value = [];
    selectedFolderMessageUid.value = null;
    folderError.value = error instanceof Error ? error.message : 'Failed to load messages';
  } finally {
    folderLoading.value = false;
  }
}

function selectFolder(role: EmailFolderRole): void {
  activeFolder.value = role;
  if (role !== 'inbox') {
    void loadFolderMessages(role);
  }
}

const selectedFolderMessage = computed(
  () =>
    folderMessages.value.find((message) => message.uid === selectedFolderMessageUid.value) ??
    null,
);

function folderMessageSenderName(message: EmailFolderMessage): string {
  const raw = String(message.from ?? '').trim();
  if (!raw) {
    return 'Unknown sender';
  }
  const match = raw.match(/^"?([^"<]+)"?\s*<[^>]+>$/);
  return (match ? match[1].trim() : raw) || 'Unknown sender';
}

watch(currentWorkspaceId, () => {
  void loadFolderTabAvailability();
  if (activeFolder.value !== 'inbox') {
    void loadFolderMessages(activeFolder.value);
  }
});

async function refreshInbox(): Promise<void> {
  refreshing.value = true;
  try {
    // loadInbox swallows its own errors into shell.inboxError -- surfaced
    // below via the existing status line, not re-thrown here.
    await shell.loadInbox({ force: true });
  } finally {
    refreshing.value = false;
  }
}

const emailItems = computed<InboxItem[]>(() =>
  [...shell.inboxItems]
    .filter((item) => item.source === 'email')
    .sort((a, b) => Date.parse(b.updated_at) - Date.parse(a.updated_at)),
);

const unreadEmailCount = computed(
  () => emailItems.value.filter((item) => !isEmailSignalRead(item.signal_id)).length,
);

const selectedItem = computed(
  () => emailItems.value.find((item) => item.signal_id === selectedSignalId.value) ?? null,
);

watch(
  emailItems,
  (items) => {
    if (selectedSignalId.value === null && items.length > 0) {
      selectItem(items[0]);
    }
  },
  { immediate: true },
);

function workspaceLabel(workspaceId: string): string {
  const record = shell.workspaces.find((ws) => ws.workspace_id === workspaceId);
  return record?.display_name?.trim() || workspaceId;
}

function senderName(item: InboxItem): string {
  const raw = String(item.meta?.sender ?? '').trim();
  if (!raw) {
    return 'Unknown sender';
  }
  // `"Display Name" <addr@host>` -> just the display name for the list row.
  const match = raw.match(/^"?([^"<]+)"?\s*<[^>]+>$/);
  return match ? match[1].trim() : raw;
}

function senderAddress(item: InboxItem): string {
  const raw = String(item.meta?.sender ?? '').trim();
  const match = raw.match(/<([^>]+)>/);
  return match ? match[1] : raw;
}

function subject(item: InboxItem): string {
  return String(item.meta?.subject ?? '').trim() || item.title;
}

function snippet(item: InboxItem): string {
  return String(item.meta?.snippet ?? '').trim() || item.summary;
}

function body(item: InboxItem): string {
  return (
    String(item.meta?.snippet ?? '').trim() ||
    String(item.summary ?? '').trim() ||
    'No message body captured for this signal.'
  );
}

function initial(item: InboxItem): string {
  const name = senderName(item);
  return name.charAt(0).toUpperCase() || '?';
}

function formatListTime(iso: string): string {
  const parsed = Date.parse(iso);
  if (Number.isNaN(parsed)) {
    return '';
  }
  const date = new Date(parsed);
  const now = new Date();
  const sameDay = date.toDateString() === now.toDateString();
  return sameDay
    ? date.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' })
    : date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}

function formatFullTime(iso: string): string {
  const parsed = Date.parse(iso);
  if (Number.isNaN(parsed)) {
    return iso;
  }
  return new Date(parsed).toLocaleString(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  });
}

function selectItem(item: InboxItem): void {
  selectedSignalId.value = item.signal_id;
  markEmailSignalRead(item.signal_id);
}

onMounted(() => {
  if (shell.inboxLoadState === 'idle' || shell.inboxLoadState === 'error') {
    void shell.loadInbox({ background: true });
  }
  void loadFolderTabAvailability();
});
</script>

<template>
  <section class="email-client" aria-label="Fleet email inbox">
    <header class="email-client__head">
      <div>
        <p class="email-client__eyebrow">Fleet-wide inbox</p>
        <p class="email-client__scope">
          {{ emailItems.length }} email{{ emailItems.length === 1 ? '' : 's' }}
          <template v-if="unreadEmailCount > 0"> · {{ unreadEmailCount }} unread</template>
        </p>
      </div>
      <div class="email-client__head-actions">
        <button
          type="button"
          class="email-client__refresh"
          :disabled="refreshing"
          :title="'Recheck every configured mailbox for new mail'"
          @click="refreshInbox"
        >
          {{ refreshing ? 'REFRESHING…' : '↻ REFRESH' }}
        </button>
        <button type="button" class="email-client__compose" @click="composeOpen = true">
          + COMPOSE
        </button>
      </div>
    </header>

    <div class="email-client__folder-tabs" role="tablist" aria-label="Mail folders">
      <button
        v-for="tab in FOLDER_TABS"
        :key="tab.role"
        type="button"
        role="tab"
        class="email-client__folder-tab"
        :class="{ 'email-client__folder-tab--active': activeFolder === tab.role }"
        :aria-selected="activeFolder === tab.role"
        :disabled="tab.role !== 'inbox' && !availableFolders[tab.role]"
        @click="selectFolder(tab.role)"
      >
        {{ tab.label }}
      </button>
    </div>

    <template v-if="activeFolder === 'inbox'">
      <p v-if="shell.inboxError" class="email-client__error" role="alert">{{ shell.inboxError }}</p>

      <p v-if="shell.inboxLoadState === 'loading' && emailItems.length === 0" class="email-client__status">
        Loading…
      </p>
      <p v-else-if="emailItems.length === 0" class="email-client__status">
        No detected emails yet.
      </p>

      <div v-else class="email-client__body">
      <ul class="email-client__list" role="listbox" aria-label="Detected emails">
        <li
          v-for="item in emailItems"
          :key="item.signal_id"
          class="email-client__row"
          :class="{
            'email-client__row--selected': item.signal_id === selectedSignalId,
            'email-client__row--unread': !isEmailSignalRead(item.signal_id),
          }"
        >
          <button
            type="button"
            class="email-client__row-button"
            role="option"
            :aria-selected="item.signal_id === selectedSignalId"
            @click="selectItem(item)"
          >
            <span class="email-client__avatar" aria-hidden="true">{{ initial(item) }}</span>
            <span class="email-client__row-main">
              <span class="email-client__row-top">
                <span class="email-client__row-sender">{{ senderName(item) }}</span>
                <span class="email-client__row-time">{{ formatListTime(item.updated_at) }}</span>
              </span>
              <span class="email-client__row-subject">{{ subject(item) }}</span>
              <span class="email-client__row-snippet">{{ snippet(item) }}</span>
              <span class="email-client__row-workspace">{{ workspaceLabel(item.workspace_id) }}</span>
            </span>
            <span v-if="!isEmailSignalRead(item.signal_id)" class="email-client__unread-dot" aria-hidden="true" />
          </button>
        </li>
      </ul>

      <div class="email-client__reading" aria-live="polite">
        <template v-if="selectedItem">
          <header class="email-client__reading-head">
            <h3 class="email-client__reading-subject">{{ subject(selectedItem) }}</h3>
            <div class="email-client__reading-meta">
              <span class="email-client__avatar email-client__avatar--lg" aria-hidden="true">
                {{ initial(selectedItem) }}
              </span>
              <div class="email-client__reading-from">
                <span class="email-client__reading-sender">{{ senderName(selectedItem) }}</span>
                <span class="email-client__reading-address">{{ senderAddress(selectedItem) }}</span>
              </div>
              <div class="email-client__reading-when">
                <span class="email-client__reading-workspace">{{ workspaceLabel(selectedItem.workspace_id) }}</span>
                <span class="email-client__reading-time">{{ formatFullTime(selectedItem.updated_at) }}</span>
              </div>
            </div>
          </header>

          <div class="email-client__reading-body">{{ body(selectedItem) }}</div>

          <p
            v-if="String(selectedItem.meta?.suggested_reply_body ?? '').trim()"
            class="email-client__reading-reply-hint"
          >
            A suggested reply for this email is waiting in the Live Ops panel →
          </p>
        </template>
        <p v-else class="email-client__status">Select an email to read it.</p>
      </div>
      </div>
    </template>

    <template v-else>
      <p v-if="folderError" class="email-client__error" role="alert">{{ folderError }}</p>
      <p v-if="folderLoading && folderMessages.length === 0" class="email-client__status">
        Loading…
      </p>
      <p v-else-if="folderMessages.length === 0" class="email-client__status">
        No messages in this folder.
      </p>

      <div v-else class="email-client__body">
        <ul class="email-client__list" role="listbox" aria-label="Folder messages">
          <li
            v-for="message in folderMessages"
            :key="message.uid"
            class="email-client__row"
            :class="{ 'email-client__row--selected': message.uid === selectedFolderMessageUid }"
          >
            <button
              type="button"
              class="email-client__row-button"
              role="option"
              :aria-selected="message.uid === selectedFolderMessageUid"
              @click="selectedFolderMessageUid = message.uid"
            >
              <span class="email-client__avatar" aria-hidden="true">
                {{ folderMessageSenderName(message).charAt(0).toUpperCase() || '?' }}
              </span>
              <span class="email-client__row-main">
                <span class="email-client__row-top">
                  <span class="email-client__row-sender">{{ folderMessageSenderName(message) }}</span>
                  <span class="email-client__row-time">{{ formatListTime(message.sent_at) }}</span>
                </span>
                <span class="email-client__row-subject">{{ message.subject || '(no subject)' }}</span>
                <span class="email-client__row-snippet">{{ message.snippet }}</span>
              </span>
            </button>
          </li>
        </ul>

        <div class="email-client__reading" aria-live="polite">
          <template v-if="selectedFolderMessage">
            <header class="email-client__reading-head">
              <h3 class="email-client__reading-subject">{{ selectedFolderMessage.subject || '(no subject)' }}</h3>
              <div class="email-client__reading-meta">
                <span class="email-client__avatar email-client__avatar--lg" aria-hidden="true">
                  {{ folderMessageSenderName(selectedFolderMessage).charAt(0).toUpperCase() || '?' }}
                </span>
                <div class="email-client__reading-from">
                  <span class="email-client__reading-sender">{{ folderMessageSenderName(selectedFolderMessage) }}</span>
                  <span class="email-client__reading-address">{{ selectedFolderMessage.from }}</span>
                </div>
                <div class="email-client__reading-when">
                  <span class="email-client__reading-time">{{ formatFullTime(selectedFolderMessage.sent_at) }}</span>
                </div>
              </div>
            </header>
            <div class="email-client__reading-body">{{ selectedFolderMessage.text || selectedFolderMessage.snippet }}</div>
          </template>
          <p v-else class="email-client__status">Select a message to read it.</p>
        </div>
      </div>
    </template>

    <EmailComposeModal v-if="composeOpen" @close="composeOpen = false" />
  </section>
</template>

<style scoped>
.email-client {
  display: grid;
  grid-template-rows: auto auto minmax(0, 1fr);
  align-content: start;
  gap: 0.6rem;
  min-height: 0;
  height: 100%;
}

.email-client__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.6rem;
}

.email-client__eyebrow {
  margin: 0;
  color: var(--accent-brand);
  font-size: 0.68rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.email-client__scope {
  margin: 0.15rem 0 0;
  color: var(--text-secondary);
  font-size: 0.75rem;
}

.email-client__folder-tabs {
  display: flex;
  align-items: center;
  gap: 0.3rem;
  border-bottom: 1px solid rgba(0, 210, 255, 0.16);
  padding-bottom: 0.4rem;
}

.email-client__folder-tab {
  display: inline-flex;
  align-items: center;
  flex: none;
  align-self: center;
  height: auto;
  line-height: 1.2;
  border: 1px solid transparent;
  border-radius: 0.25rem;
  padding: 0.3rem 0.6rem;
  background: none;
  color: var(--text-secondary);
  font-size: 0.68rem;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.email-client__folder-tab:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}

.email-client__folder-tab--active {
  border-color: rgba(0, 210, 255, 0.34);
  background: rgba(0, 120, 160, 0.2);
  color: var(--accent-brand);
}

.email-client__head-actions {
  display: flex;
  align-items: center;
  gap: 0.4rem;
}

.email-client__compose,
.email-client__refresh {
  border: 1px solid rgba(0, 210, 255, 0.34);
  border-radius: 0.25rem;
  padding: 0.38rem 0.7rem;
  background: rgba(0, 120, 160, 0.2);
  color: var(--accent-brand);
  font-size: 0.68rem;
  letter-spacing: 0.08em;
  white-space: nowrap;
}

.email-client__refresh:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.email-client__status {
  margin: 0;
  color: var(--text-secondary);
  font-size: 0.78rem;
}

.email-client__error {
  margin: 0;
  color: var(--state-critical);
  font-size: 0.75rem;
}

.email-client__body {
  display: grid;
  grid-template-columns: minmax(220px, 320px) minmax(0, 1fr);
  grid-template-rows: minmax(0, 1fr);
  gap: 0.6rem;
  min-height: 0;
  height: 100%;
  overflow: hidden;
}

.email-client__list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  overflow-y: auto;
  min-height: 0;
  max-height: none;
  border: 1px solid rgba(0, 210, 255, 0.16);
  border-radius: 0.4rem;
  background: rgba(0, 12, 20, 0.4);
  padding: 0.3rem;
}

.email-client__row-button {
  position: relative;
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
  width: 100%;
  border: none;
  border-radius: 0.3rem;
  background: none;
  padding: 0.45rem 0.5rem;
  text-align: left;
  color: var(--text-primary);
  font: inherit;
}

.email-client__row--unread .email-client__row-sender,
.email-client__row--unread .email-client__row-subject {
  font-weight: 700;
}

.email-client__row--selected .email-client__row-button {
  background: rgba(0, 150, 200, 0.18);
}

.email-client__row-button:hover {
  background: rgba(0, 150, 200, 0.1);
}

.email-client__avatar {
  flex: none;
  width: 1.7rem;
  height: 1.7rem;
  border-radius: 50%;
  display: grid;
  place-items: center;
  background: rgba(0, 210, 255, 0.18);
  color: var(--accent-brand);
  font-size: 0.72rem;
  font-weight: 700;
}

.email-client__avatar--lg {
  width: 2.4rem;
  height: 2.4rem;
  font-size: 0.95rem;
}

.email-client__row-main {
  display: flex;
  flex-direction: column;
  gap: 0.1rem;
  min-width: 0;
  flex: 1;
}

.email-client__row-top {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 0.4rem;
}

.email-client__row-sender {
  font-size: 0.76rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.email-client__row-time {
  flex: none;
  color: var(--text-secondary);
  font-size: 0.64rem;
  white-space: nowrap;
}

.email-client__row-subject {
  font-size: 0.74rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.email-client__row-snippet {
  color: var(--text-secondary);
  font-size: 0.68rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.email-client__row-workspace {
  margin-top: 0.1rem;
  color: var(--accent-brand);
  font-size: 0.6rem;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.email-client__unread-dot {
  position: absolute;
  top: 0.55rem;
  right: 0.5rem;
  width: 0.4rem;
  height: 0.4rem;
  border-radius: 50%;
  background: var(--accent-brand);
}

.email-client__reading {
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
  min-width: 0;
  overflow-y: auto;
  min-height: 0;
  max-height: none;
  border: 1px solid rgba(0, 210, 255, 0.16);
  border-radius: 0.4rem;
  background: rgba(0, 12, 20, 0.4);
  padding: 0.8rem 0.9rem;
}

.email-client__reading-head {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  border-bottom: 1px solid rgba(0, 210, 255, 0.14);
  padding-bottom: 0.6rem;
}

.email-client__reading-subject {
  margin: 0;
  font-size: 1rem;
  color: var(--text-primary);
}

.email-client__reading-meta {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.email-client__reading-from {
  display: flex;
  flex-direction: column;
  min-width: 0;
  flex: 1;
}

.email-client__reading-sender {
  font-size: 0.8rem;
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.email-client__reading-address {
  color: var(--text-secondary);
  font-size: 0.68rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.email-client__reading-when {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  text-align: right;
  flex: none;
}

.email-client__reading-workspace {
  color: var(--accent-brand);
  font-size: 0.62rem;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.email-client__reading-time {
  color: var(--text-secondary);
  font-size: 0.68rem;
}

.email-client__reading-body {
  white-space: pre-wrap;
  color: var(--text-primary);
  font-size: 0.8rem;
  line-height: 1.55;
}

.email-client__reading-reply-hint {
  margin: 0;
  border-top: 1px solid rgba(0, 210, 255, 0.14);
  padding-top: 0.6rem;
  color: var(--accent-brand);
  font-size: 0.72rem;
}

@media (max-width: 900px) {
  .email-client__body {
    grid-template-columns: minmax(0, 1fr);
    grid-template-rows: auto auto;
    height: auto;
    overflow: visible;
  }

  .email-client__list {
    max-height: 30vh;
  }

  .email-client__reading {
    max-height: 45vh;
  }
}
</style>

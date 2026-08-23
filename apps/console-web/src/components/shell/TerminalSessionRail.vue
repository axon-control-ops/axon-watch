<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue';

import WorkbenchIcon from '../WorkbenchIcon.vue';
import {
  DEFAULT_OPERATOR_TERMINAL_SESSION_ID,
  terminalSessionBranchBadge,
  terminalSessionRootTitle,
  terminalSessionTabLabel,
} from '../../lib/terminal-session-view';

type TerminalSessionRow = {
  id: string;
  title: string;
  role: 'operator' | 'agent' | string;
  runId: string | null;
  cwd?: string;
  branch?: string;
  isolated?: boolean;
};

const props = defineProps<{
  sessions: TerminalSessionRow[];
  activeSessionId: string | null;
  workspaceId: string;
}>();

const emit = defineEmits<{
  select: [sessionId: string];
  split: [sessionId: string];
  kill: [sessionId: string];
  rename: [sessionId: string, title: string];
}>();

type ContextMenuState = {
  sessionId: string;
  x: number;
  y: number;
};

const contextMenu = ref<ContextMenuState | null>(null);
const renamingSessionId = ref<string | null>(null);
const renameDraft = ref('');
const renameInputRef = ref<HTMLInputElement | null>(null);
const contextSession = computed(() =>
  props.sessions.find((session) => session.id === contextMenu.value?.sessionId) ?? null,
);

function toRecord(session: TerminalSessionRow) {
  return {
    session_id: session.id,
    workspace_id: props.workspaceId,
    role: session.role,
    title: session.title,
    run_id: session.runId,
    created_at: '',
    cwd: session.cwd,
    branch: session.branch,
    isolated: session.isolated,
  };
}

function sessionLabel(session: TerminalSessionRow): string {
  return terminalSessionTabLabel(toRecord(session));
}

function branchBadge(session: TerminalSessionRow): string {
  return terminalSessionBranchBadge(toRecord(session));
}

function rootTitle(session: TerminalSessionRow): string {
  return terminalSessionRootTitle(toRecord(session));
}

function closeContextMenu(): void {
  contextMenu.value = null;
}

function openContextMenu(event: MouseEvent, sessionId: string): void {
  event.preventDefault();
  event.stopPropagation();
  contextMenu.value = {
    sessionId,
    x: Math.min(event.clientX, window.innerWidth - 168),
    y: Math.min(event.clientY, window.innerHeight - 140),
  };
}

function handleDocumentPointerDown(event: PointerEvent): void {
  const target = event.target as HTMLElement | null;
  if (!target?.closest('.terminal-session-rail__context-menu')) {
    closeContextMenu();
  }
}

function handleDocumentKeydown(event: KeyboardEvent): void {
  if (event.key === 'Escape') {
    closeContextMenu();
    cancelRename();
  }
}

async function beginRename(session: TerminalSessionRow): Promise<void> {
  closeContextMenu();
  renamingSessionId.value = session.id;
  renameDraft.value = sessionLabel(session);
  await nextTick();
  renameInputRef.value?.focus();
  renameInputRef.value?.select();
}

function cancelRename(): void {
  renamingSessionId.value = null;
  renameDraft.value = '';
}

function commitRename(): void {
  const sessionId = renamingSessionId.value;
  if (!sessionId) {
    return;
  }
  const title = renameDraft.value.trim();
  cancelRename();
  if (title) {
    emit('rename', sessionId, title);
  }
}

function handleRenameKeydown(event: KeyboardEvent): void {
  if (event.key === 'Enter') {
    event.preventDefault();
    commitRename();
  } else if (event.key === 'Escape') {
    event.preventDefault();
    cancelRename();
  }
}

function onSplit(sessionId: string, event?: Event): void {
  event?.preventDefault();
  event?.stopPropagation();
  closeContextMenu();
  emit('split', sessionId);
}

function onKill(sessionId: string, event?: Event): void {
  event?.preventDefault();
  event?.stopPropagation();
  closeContextMenu();
  if (sessionId === DEFAULT_OPERATOR_TERMINAL_SESSION_ID) {
    return;
  }
  emit('kill', sessionId);
}

onMounted(() => {
  document.addEventListener('pointerdown', handleDocumentPointerDown, true);
  document.addEventListener('keydown', handleDocumentKeydown);
});

onBeforeUnmount(() => {
  document.removeEventListener('pointerdown', handleDocumentPointerDown, true);
  document.removeEventListener('keydown', handleDocumentKeydown);
});
</script>

<template>
  <aside class="terminal-session-rail" aria-label="Terminal sessions">
    <div class="terminal-session-rail__list" role="tablist" aria-orientation="vertical">
      <div
        v-for="session in sessions"
        :key="session.id"
        class="terminal-session-rail__row"
        :class="{
          'is-active': activeSessionId === session.id,
          'is-agent': session.role === 'agent',
          'is-renaming': renamingSessionId === session.id,
        }"
      >
        <button
          type="button"
          role="tab"
          class="terminal-session-rail__item"
          :aria-selected="activeSessionId === session.id"
          @click="emit('select', session.id)"
          @contextmenu="openContextMenu($event, session.id)"
        >
          <WorkbenchIcon
            :name="session.role === 'agent' ? 'terminal-agent' : 'terminal'"
            :size="14"
            class="terminal-session-rail__shell-icon"
          />
          <input
            v-if="renamingSessionId === session.id"
            ref="renameInputRef"
            v-model="renameDraft"
            class="terminal-session-rail__rename-input"
            aria-label="Rename terminal"
            @click.stop
            @keydown="handleRenameKeydown"
            @blur="commitRename"
          >
          <span v-else class="terminal-session-rail__label" :title="rootTitle(session)">
            {{ sessionLabel(session) }}
            <span
              v-if="branchBadge(session)"
              class="terminal-session-rail__branch"
              :title="rootTitle(session)"
            >{{ branchBadge(session) }}</span>
          </span>
        </button>

        <div class="terminal-session-rail__hover-actions">
          <button
            type="button"
            class="terminal-session-rail__icon-btn"
            :title="session.role === 'agent' ? 'Split with zsh terminal' : 'Split Terminal'"
            :aria-label="session.role === 'agent' ? 'Split with zsh local terminal' : 'Split Terminal'"
            @click="onSplit(session.id, $event)"
          >
            <WorkbenchIcon name="split" :size="13" />
          </button>
          <button
            type="button"
            class="terminal-session-rail__icon-btn"
            :title="session.id === DEFAULT_OPERATOR_TERMINAL_SESSION_ID ? 'The default terminal stays available' : 'Kill Terminal'"
            :aria-label="session.id === DEFAULT_OPERATOR_TERMINAL_SESSION_ID ? 'Default terminal cannot be killed' : 'Kill Terminal'"
            :disabled="session.id === DEFAULT_OPERATOR_TERMINAL_SESSION_ID"
            @click="onKill(session.id, $event)"
          >
            <WorkbenchIcon name="trash" :size="14" />
          </button>
        </div>
      </div>
    </div>

    <Teleport to="body">
      <div
        v-if="contextMenu && contextSession"
        class="terminal-session-rail__context-menu"
        role="menu"
        :style="{ left: `${contextMenu.x}px`, top: `${contextMenu.y}px` }"
        @pointerdown.stop
      >
        <button
          v-if="contextSession.id !== DEFAULT_OPERATOR_TERMINAL_SESSION_ID"
          type="button"
          class="terminal-session-rail__context-item"
          role="menuitem"
          @click="onSplit(contextSession.id)"
        >
          Split
        </button>
        <button
          type="button"
          class="terminal-session-rail__context-item"
          role="menuitem"
          @click="beginRename(contextSession)"
        >
          Rename…
        </button>
        <div class="terminal-session-rail__context-sep" />
        <button
          type="button"
          class="terminal-session-rail__context-item terminal-session-rail__context-item--danger"
          role="menuitem"
          @click="onKill(contextSession.id)"
        >
          Kill Terminal
        </button>
      </div>
    </Teleport>
  </aside>
</template>

<style scoped>
.terminal-session-rail {
  display: flex;
  flex-direction: column;
  flex: 0 0 10.5rem;
  width: 10.5rem;
  min-width: 9.5rem;
  max-width: 13rem;
  border-left: 1px solid rgba(138, 154, 173, 0.18);
  background: #031018;
  min-height: 0;
  overflow: visible;
}

.terminal-session-rail__list {
  display: flex;
  flex-direction: column;
  gap: 0.08rem;
  padding: 0.28rem 0.2rem;
  overflow-x: hidden;
  overflow-y: auto;
  min-height: 0;
  flex: 1;
}

.terminal-session-rail__row {
  display: flex;
  align-items: center;
  gap: 0.1rem;
  min-height: 1.75rem;
  padding: 0 0.15rem 0 0;
  border-left: 2px solid transparent;
  border-radius: 0.2rem;
}

.terminal-session-rail__row:hover,
.terminal-session-rail__row.is-active {
  background: rgba(255, 255, 255, 0.05);
}

.terminal-session-rail__row.is-active {
  border-left-color: rgba(0, 180, 255, 0.9);
}

.terminal-session-rail__row.is-agent.is-active {
  border-left-color: rgba(167, 139, 250, 0.95);
}

.terminal-session-rail__item {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  flex: 1 1 auto;
  min-width: 0;
  min-height: 1.75rem;
  padding: 0.2rem 0.3rem 0.2rem 0.4rem;
  border: 0;
  border-radius: 0.18rem;
  background: transparent;
  color: rgba(168, 186, 204, 0.9);
  font-family: var(--font-mono, ui-monospace, monospace);
  font-size: 0.64rem;
  letter-spacing: 0.02em;
  text-align: left;
  cursor: pointer;
}

.terminal-session-rail__row.is-active .terminal-session-rail__item,
.terminal-session-rail__row:hover .terminal-session-rail__item {
  color: rgba(230, 242, 255, 0.98);
}

.terminal-session-rail__row.is-agent .terminal-session-rail__item {
  color: rgba(196, 180, 255, 0.92);
}

.terminal-session-rail__shell-icon {
  flex-shrink: 0;
  opacity: 0.78;
  margin-right: 0.02rem;
}

.terminal-session-rail__label {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.terminal-session-rail__branch {
  margin-left: 0.3rem;
  padding: 0 0.28rem;
  border-radius: 3px;
  background: rgba(250, 204, 21, 0.16);
  color: rgb(250, 204, 21);
  font-size: 0.56rem;
  vertical-align: middle;
}

.terminal-session-rail__rename-input {
  flex: 1;
  min-width: 0;
  border: 1px solid rgba(0, 210, 255, 0.5);
  border-radius: 0.15rem;
  background: rgba(4, 14, 22, 0.95);
  color: rgba(230, 242, 255, 0.96);
  font: inherit;
  font-size: 0.62rem;
  line-height: 1.2;
  padding: 0.08rem 0.22rem;
  outline: none;
}

.terminal-session-rail__hover-actions {
  display: inline-flex;
  align-items: center;
  gap: 0.05rem;
  flex: 0 0 auto;
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.08s ease;
}

.terminal-session-rail__row:hover .terminal-session-rail__hover-actions,
.terminal-session-rail__row.is-active .terminal-session-rail__hover-actions,
.terminal-session-rail__row:focus-within .terminal-session-rail__hover-actions {
  opacity: 1;
  pointer-events: auto;
}

.terminal-session-rail__row.is-renaming .terminal-session-rail__hover-actions {
  opacity: 0;
  pointer-events: none;
}

.terminal-session-rail__icon-btn {
  display: inline-grid;
  place-items: center;
  width: 1.4rem;
  height: 1.4rem;
  padding: 0;
  border: 0;
  border-radius: 0.2rem;
  background: transparent;
  color: rgba(168, 186, 204, 0.92);
  cursor: pointer;
}

.terminal-session-rail__icon-btn:hover {
  background: rgba(255, 255, 255, 0.1);
  color: rgba(230, 242, 255, 0.98);
}

.terminal-session-rail__icon-btn:disabled {
  cursor: default;
  opacity: 0.35;
}

.terminal-session-rail__icon-btn:disabled:hover {
  background: transparent;
  color: rgba(168, 186, 204, 0.92);
}
</style>

<!-- Teleported menu lives on <body>; scoped attrs do not apply there. -->
<style>
.terminal-session-rail__context-menu {
  position: fixed;
  z-index: 4000;
  min-width: 9rem;
  padding: 0.28rem;
  border: 1px solid rgba(0, 242, 255, 0.22);
  border-radius: 0.35rem;
  background: rgba(4, 16, 24, 0.98);
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.55);
}

.terminal-session-rail__context-item {
  display: block;
  width: 100%;
  border: 0;
  border-radius: 0.25rem;
  background: transparent;
  color: rgba(210, 224, 236, 0.96);
  cursor: pointer;
  font: inherit;
  font-size: 0.72rem;
  line-height: 1.2;
  padding: 0.42rem 0.55rem;
  text-align: left;
}

.terminal-session-rail__context-item:hover {
  background: rgba(0, 242, 255, 0.1);
  color: rgba(180, 240, 255, 0.98);
}

.terminal-session-rail__context-item--danger:hover {
  background: rgba(255, 111, 111, 0.14);
  color: rgba(255, 180, 180, 0.98);
}

.terminal-session-rail__context-sep {
  height: 1px;
  margin: 0.2rem 0.35rem;
  background: rgba(138, 154, 173, 0.2);
}
</style>

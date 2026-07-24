<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue';

import TerminalHost from './TerminalHost.vue';
import WorkbenchIcon from './WorkbenchIcon.vue';
import OperatorJarvisOpsPanel from './shell/OperatorJarvisOpsPanel.vue';
import TerminalSessionRail from './shell/TerminalSessionRail.vue';
import { useAgentTerminalMirror } from '../composables/useAgentTerminalMirror';
import {
  agentShellMirrorActive,
  agentShellMirrorForcedText,
  armAgentShellMirror,
  clearAgentShellMirror,
  pendingAgentBackgroundCommand,
  pendingOperatorTerminalCommand,
  takePendingAgentBackgroundCommand,
  takePendingOperatorTerminalCommand,
} from '../lib/agent-shell-mirror-state';
import { terminalSessionTabLabel } from '../lib/terminal-session-view';
import {
  resolveActiveVisibleTerminalSessionIds,
  resolveMirrorVisibleTerminalSessionIds,
} from '../lib/workbench-terminal-visible-panes';
import { resolveAgentTerminalMirrorTranscript } from '../lib/workbench-terminal-mirror-transcript';
import {
  workbenchTerminalPanelAriaLabel,
  workbenchTerminalPanelTitle,
} from '../lib/workbench-terminal-panel-view';
import { useShellStore } from '../stores/shell';

const props = defineProps<{
  hideOperatorEditor: boolean;
  logLines: string[];
  outputLines: string[];
  problemItems: string[];
  terminalHeight: number;
}>();

const emit = defineEmits<{
  hide: [];
  'start-resize': [event: MouseEvent];
}>();

type BottomTabId = 'ops' | 'terminal' | 'problems' | 'output' | 'logs';
type TerminalHostInstance = InstanceType<typeof TerminalHost>;

const shell = useShellStore();
const bottomTab = ref<BottomTabId>(props.hideOperatorEditor ? 'ops' : 'terminal');
const showNewTerminalMenu = ref(false);
const terminalHostRefs = ref<Record<string, TerminalHostInstance | null>>({});
const visibleTerminalSessionIds = ref<string[]>([]);

const activeTerminalSession = computed(() => shell.activeTerminalSession);
const bottomTabs = computed(() => [
  { id: 'ops' as const, label: 'OPS' },
  { id: 'terminal' as const, label: 'TERMINAL' },
  { id: 'problems' as const, label: `PROBLEMS ${props.problemItems.length}` },
  { id: 'output' as const, label: 'OUTPUT' },
  { id: 'logs' as const, label: 'LOGS' },
]);

watch(
  () => props.hideOperatorEditor,
  (operatorMode) => {
    if (operatorMode && bottomTab.value === 'terminal') {
      bottomTab.value = 'ops';
    }
  },
);

const visibleTerminalSessions = computed(() => {
  const orderedIds = visibleTerminalSessionIds.value.length
    ? visibleTerminalSessionIds.value
    : [shell.activeTerminalSessionId];
  const seen = new Set<string>();
  const sessions = orderedIds
    .map((id) => shell.terminalSessions.find((session) => session.id === id) ?? null)
    .filter((session): session is (typeof shell.terminalSessions)[number] => {
      if (!session || seen.has(session.id)) {
        return false;
      }
      seen.add(session.id);
      return true;
    });
  if (!sessions.length) {
    sessions.push(shell.activeTerminalSession);
  }
  return sessions.slice(0, 2);
});

const agentSessionId = computed(
  () => shell.terminalSessions.find((session) => session.role === 'agent')?.id ?? null,
);

const agentStreamActive = computed(() => shell.agentStreamActive);

const terminalRunPhase = computed(() => shell.primaryActiveRun?.phase ?? null);

function resolveMirrorTranscriptContent(): string {
  return resolveAgentTerminalMirrorTranscript({
    streamMessageId: shell.agentStreamMessageId,
    threadMessages: shell.threadMessages,
  });
}

const { syncNow: syncAgentTerminalMirror } = useAgentTerminalMirror({
  mirrorActive: agentShellMirrorActive,
  agentSessionId,
  getTranscriptContent: resolveMirrorTranscriptContent,
  streamActive: agentStreamActive,
  clearMirror: clearAgentShellMirror,
  forcedText: agentShellMirrorForcedText,
  getHost: (sessionId) => terminalHostRefs.value[sessionId] ?? null,
});

watch(
  () => [agentShellMirrorActive.value, agentShellMirrorForcedText.value, agentSessionId.value] as const,
  ([active, forced, sessionId]) => {
    if (!active || !sessionId) {
      return;
    }
    if (!forced && !resolveMirrorTranscriptContent()) {
      return;
    }
    // Focus the existing agent/vaxon pane only — never auto-split beside bash.
    visibleTerminalSessionIds.value = resolveMirrorVisibleTerminalSessionIds(sessionId);
    // Host may mount one tick after the agent session becomes active.
    requestAnimationFrame(() => {
      syncAgentTerminalMirror();
    });
  },
);

function paneLabel(session: (typeof shell.terminalSessions)[number]): string {
  const base = terminalSessionTabLabel({
    session_id: session.id,
    workspace_id: shell.currentWorkspace?.workspace_id ?? '',
    role: session.role,
    title: session.title,
    run_id: session.runId,
    created_at: '',
  });
  if (session.role === 'agent' && agentShellMirrorActive.value) {
    return `${base} · agent shell`;
  }
  return session.role === 'agent' ? `${base} · read-only` : base;
}

function setTerminalHostRef(sessionId: string, host: TerminalHostInstance | null): void {
  terminalHostRefs.value = {
    ...terminalHostRefs.value,
    [sessionId]: host,
  };
  if (!host) {
    return;
  }
  if (sessionId === agentSessionId.value) {
    if (agentShellMirrorForcedText.value || agentShellMirrorActive.value) {
      if (agentShellMirrorForcedText.value) {
        armAgentShellMirror();
      }
      syncAgentTerminalMirror();
    }
  }
  flushPendingOperatorCommand(sessionId);
  flushPendingAgentBackgroundCommand(sessionId);
}

function flushPendingOperatorCommand(sessionId?: string): void {
  const command = pendingOperatorTerminalCommand.value;
  if (!command) {
    return;
  }
  const operatorSession = shell.terminalSessions.find((session) => session.role === 'operator');
  if (!operatorSession) {
    return;
  }
  if (sessionId && sessionId !== operatorSession.id) {
    return;
  }
  if (shell.activeTerminalSessionId !== operatorSession.id) {
    return;
  }
  const host = terminalHostRefs.value[operatorSession.id];
  if (!host?.writeInput) {
    return;
  }
  takePendingOperatorTerminalCommand();
  visibleTerminalSessionIds.value = [operatorSession.id];
  // Give the PTY a tick to finish ready handshake when freshly focused.
  requestAnimationFrame(() => {
    host.writeInput(`${command}\r`);
  });
}

function flushPendingAgentBackgroundCommand(sessionId?: string): void {
  const command = pendingAgentBackgroundCommand.value;
  if (!command) {
    return;
  }
  const agentSession = shell.terminalSessions.find((session) => session.role === 'agent');
  if (!agentSession) {
    return;
  }
  if (sessionId && sessionId !== agentSession.id) {
    return;
  }
  if (shell.activeTerminalSessionId !== agentSession.id) {
    return;
  }
  const host = terminalHostRefs.value[agentSession.id] as
    | { writeInput?: (data: string) => void; exitMirrorMode?: () => void }
    | undefined;
  if (!host?.writeInput) {
    return;
  }
  takePendingAgentBackgroundCommand();
  clearAgentShellMirror();
  host.exitMirrorMode?.();
  visibleTerminalSessionIds.value = [agentSession.id];
  requestAnimationFrame(() => {
    host.writeInput?.(`${command}\r`);
  });
}

watch(pendingOperatorTerminalCommand, (command) => {
  if (!command) {
    return;
  }
  const operatorSession = shell.terminalSessions.find((session) => session.role === 'operator');
  if (!operatorSession) {
    return;
  }
  visibleTerminalSessionIds.value = [operatorSession.id];
  if (shell.activeTerminalSessionId !== operatorSession.id) {
    shell.setActiveTerminalSession(operatorSession.id);
  }
  requestAnimationFrame(() => {
    flushPendingOperatorCommand(operatorSession.id);
  });
});

watch(pendingAgentBackgroundCommand, (command) => {
  if (!command) {
    return;
  }
  const agentSession = shell.terminalSessions.find((session) => session.role === 'agent');
  if (!agentSession) {
    return;
  }
  visibleTerminalSessionIds.value = [agentSession.id];
  if (shell.activeTerminalSessionId !== agentSession.id) {
    shell.setActiveTerminalSession(agentSession.id);
  }
  requestAnimationFrame(() => {
    flushPendingAgentBackgroundCommand(agentSession.id);
  });
});

function closeNewTerminalMenu(): void {
  showNewTerminalMenu.value = false;
}

function handleDocumentPointerDown(event: PointerEvent): void {
  const target = event.target as HTMLElement | null;
  if (showNewTerminalMenu.value && !target?.closest('.terminal-tabbar__new-wrap')) {
    showNewTerminalMenu.value = false;
  }
}

function createTerminalSession(kind: 'bash' | 'zsh' | 'vaxon' = 'bash'): void {
  closeNewTerminalMenu();
  if (kind === 'vaxon') {
    void shell.createVaxonTerminalSession();
    return;
  }
  void shell.createTerminalSession({
    role: 'operator',
    title: kind,
  });
}

function toggleNewTerminalMenu(): void {
  showNewTerminalMenu.value = !showNewTerminalMenu.value;
}

function selectTerminalSession(sessionId: string): void {
  if (visibleTerminalSessionIds.value.includes(sessionId)) {
    shell.setActiveTerminalSession(sessionId);
    return;
  }
  if (visibleTerminalSessionIds.value.length > 1) {
    visibleTerminalSessionIds.value = visibleTerminalSessionIds.value.map((id) =>
      id === shell.activeTerminalSessionId ? sessionId : id,
    );
  } else {
    visibleTerminalSessionIds.value = [sessionId];
  }
  shell.setActiveTerminalSession(sessionId);
}

async function splitTerminalSession(sessionId: string): Promise<void> {
  const createdSessionId = await shell.splitTerminalSession(sessionId);
  if (!createdSessionId) {
    return;
  }
  visibleTerminalSessionIds.value = [sessionId, createdSessionId];
  shell.setActiveTerminalSession(createdSessionId);
}

function handleHeaderSplit(): void {
  void splitTerminalSession(activeTerminalSession.value.id);
}

function killTerminalSession(sessionId: string): void {
  void shell.closeTerminalSession(sessionId);
}

function handleHeaderKill(): void {
  killTerminalSession(activeTerminalSession.value.id);
}

function renameTerminalSession(sessionId: string, title: string): void {
  void shell.renameTerminalSession(sessionId, title);
}

function clearTerminalPanel(): void {
  terminalHostRefs.value[shell.activeTerminalSessionId]?.clearTerminal();
}

function requestHideTerminalPanel(): void {
  closeNewTerminalMenu();
  emit('hide');
}

watch(
  () => [shell.activeTerminalSessionId, shell.terminalSessions.map((session) => session.id).join('|')],
  () => {
    const existingIds = new Set(shell.terminalSessions.map((session) => session.id));
    visibleTerminalSessionIds.value = resolveActiveVisibleTerminalSessionIds({
      visibleSessionIds: visibleTerminalSessionIds.value,
      existingSessionIds: existingIds,
      activeSessionId: shell.activeTerminalSessionId,
    });
  },
  { immediate: true },
);

watch(
  () => shell.ideTerminalRevealToken,
  () => {
    bottomTab.value = 'terminal';
  },
);

onMounted(() => {
  document.addEventListener('pointerdown', handleDocumentPointerDown, true);
});

onBeforeUnmount(() => {
  document.removeEventListener('pointerdown', handleDocumentPointerDown, true);
});
</script>

<template>
  <div
    class="center-workbench__bottom-dock center-workbench__bottom-dock--surface"
    :style="{ height: `${terminalHeight}px` }"
  >
    <section class="center-workbench__terminal-panel center-workbench__terminal-panel--mockup">
      <div
        class="center-workbench__resize-handle"
        role="separator"
        aria-orientation="horizontal"
        aria-label="Resize terminal panel"
        tabindex="0"
        @mousedown="emit('start-resize', $event)"
      >
        <span class="center-workbench__resize-grip" aria-hidden="true" />
      </div>

      <div class="terminal-tabbar terminal-tabbar--mockup">
        <div class="terminal-tabbar__tabs">
          <button
            v-for="tab in bottomTabs"
            :key="tab.id"
            type="button"
            class="terminal-tabbar__tab hud-active-chip hud-active-chip--tab"
            :class="{ 'terminal-tabbar__tab--active hud-active-chip--active': bottomTab === tab.id }"
            @click="bottomTab = tab.id"
          >
            {{ tab.label }}
          </button>
        </div>
        <div class="terminal-tabbar__actions">
          <div class="terminal-tabbar__new-wrap">
            <button
              type="button"
              class="terminal-tabbar__action-button"
              title="New terminal"
              aria-label="New terminal"
              aria-haspopup="menu"
              :aria-expanded="showNewTerminalMenu"
              @click.stop="toggleNewTerminalMenu"
            >
              <WorkbenchIcon name="plus" class="terminal-tabbar__action" :size="18" />
            </button>
            <div
              v-if="showNewTerminalMenu"
              class="terminal-tabbar__new-menu"
              role="menu"
              aria-label="Create terminal session"
            >
              <button
                type="button"
                class="terminal-tabbar__new-menu-item"
                role="menuitem"
                @click="createTerminalSession('bash')"
              >
                bash
              </button>
              <button
                type="button"
                class="terminal-tabbar__new-menu-item"
                role="menuitem"
                @click="createTerminalSession('zsh')"
              >
                zsh
              </button>
              <button
                type="button"
                class="terminal-tabbar__new-menu-item terminal-tabbar__new-menu-item--agent"
                role="menuitem"
                @click="createTerminalSession('vaxon')"
              >
                vaxon
              </button>
            </div>
          </div>
          <button
            type="button"
            class="terminal-tabbar__action-button"
            :title="activeTerminalSession.role === 'agent' ? 'Split with bash terminal' : 'Split terminal'"
            :aria-label="activeTerminalSession.role === 'agent' ? 'Split with bash terminal' : 'Split terminal'"
            @click="handleHeaderSplit"
          >
            <WorkbenchIcon name="split" class="terminal-tabbar__action" :size="18" />
          </button>
          <button
            type="button"
            class="terminal-tabbar__action-button"
            title="Kill terminal"
            aria-label="Kill terminal"
            @click="handleHeaderKill"
          >
            <WorkbenchIcon name="trash" class="terminal-tabbar__action" :size="18" />
          </button>
          <button
            type="button"
            class="terminal-tabbar__action-button"
            title="Clear terminal"
            aria-label="Clear terminal"
            @click="clearTerminalPanel"
          >
            <WorkbenchIcon name="trash" class="terminal-tabbar__action" :size="18" />
          </button>
          <button
            type="button"
            class="terminal-tabbar__action-button"
            :title="workbenchTerminalPanelTitle(true, terminalRunPhase)"
            :aria-label="workbenchTerminalPanelAriaLabel(true, terminalRunPhase)"
            @click="requestHideTerminalPanel"
          >
            <WorkbenchIcon name="close" class="terminal-tabbar__action" :size="18" />
          </button>
        </div>
      </div>

      <div v-if="bottomTab === 'ops'" class="center-workbench__panel-surface center-workbench__panel-surface--ops">
        <OperatorJarvisOpsPanel />
      </div>
      <div v-else-if="bottomTab === 'terminal'" class="center-workbench__terminal-body center-workbench__terminal-body--with-rail">
        <div class="center-workbench__terminal-main">
          <div class="center-workbench__terminal-stack">
            <div
              v-for="session in visibleTerminalSessions"
              :key="session.id"
              class="center-workbench__terminal-pane"
              :class="{ 'center-workbench__terminal-pane--active': session.id === shell.activeTerminalSessionId }"
            >
              <div
                v-if="visibleTerminalSessions.length > 1 || session.role === 'agent'"
                class="center-workbench__terminal-pane-label"
              >
                {{ paneLabel(session) }}
              </div>
              <TerminalHost
                :ref="(host) => setTerminalHostRef(session.id, host as InstanceType<typeof TerminalHost> | null)"
                variant="mockup"
                :workspace-id="shell.currentWorkspace?.workspace_id ?? null"
                :session-id="session.id"
                :session-role="session.role"
                :read-only="session.role === 'agent'"
                :run-summary="
                  shell.primaryActiveRun
                    ? `${shell.primaryActiveRun.run_id} · ${shell.primaryActiveRun.phase} · ${shell.primaryActiveRun.status}`
                    : null
                "
                :primary-signal-id="shell.workspacePrimarySignal?.signal_id ?? null"
                :runtime-connected="Boolean(shell.runtimeSummary?.watch.connected)"
              />
            </div>
          </div>
        </div>
        <TerminalSessionRail
          :sessions="shell.terminalSessions"
          :active-session-id="shell.activeTerminalSessionId"
          :workspace-id="shell.currentWorkspace?.workspace_id ?? ''"
          @select="selectTerminalSession"
          @split="splitTerminalSession"
          @kill="killTerminalSession"
          @rename="renameTerminalSession"
        />
      </div>
      <div v-else-if="bottomTab === 'problems'" class="center-workbench__panel-surface">
        <p v-if="problemItems.length === 0" class="center-workbench__panel-empty region-copy">
          No active problems. Runtime, save, briefing, and run surfaces are clear.
        </p>
        <ul v-else class="center-workbench__panel-list">
          <li
            v-for="item in problemItems"
            :key="item"
            class="center-workbench__panel-item center-workbench__panel-item--problem"
          >
            {{ item }}
          </li>
        </ul>
      </div>
      <div v-else-if="bottomTab === 'output'" class="center-workbench__panel-surface">
        <ul class="center-workbench__panel-list">
          <li v-for="item in outputLines" :key="item" class="center-workbench__panel-item">
            {{ item }}
          </li>
        </ul>
      </div>
      <div v-else class="center-workbench__panel-surface">
        <ul class="center-workbench__panel-list">
          <li v-for="item in logLines" :key="item" class="center-workbench__panel-item center-workbench__panel-item--log">
            {{ item }}
          </li>
        </ul>
      </div>
    </section>
  </div>
</template>

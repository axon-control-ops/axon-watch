<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue';

import TerminalHost from './TerminalHost.vue';
import WorkbenchIcon from './WorkbenchIcon.vue';
import OperatorJarvisOpsPanel from './shell/OperatorJarvisOpsPanel.vue';
import TerminalNewSessionMenu from './shell/TerminalNewSessionMenu.vue';
import TerminalSessionRail from './shell/TerminalSessionRail.vue';
import { useAgentTerminalMirror } from '../composables/useAgentTerminalMirror';
import {
  agentShellMirrorActive,
  agentShellMirrorForcedText,
  armAgentShellMirror,
  clearAgentShellMirror,
  pendingAgentBackgroundCommand,
  pendingOperatorTerminalCommand,
} from '../lib/agent-shell-mirror-state';
import {
  flushPendingAgentBackgroundTerminalCommand,
  flushPendingOperatorTerminalCommand,
  focusSessionForPendingCommand,
} from '../lib/workbench-terminal-pending-commands';
import {
  DEFAULT_OPERATOR_TERMINAL_SESSION_ID,
  terminalSessionTabLabel,
} from '../lib/terminal-session-view';
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
const terminalActionError = ref<string | null>(null);
let terminalActionErrorTimer: ReturnType<typeof setTimeout> | null = null;

function flashTerminalActionError(message: string): void {
  terminalActionError.value = message;
  if (terminalActionErrorTimer) clearTimeout(terminalActionErrorTimer);
  terminalActionErrorTimer = setTimeout(() => (terminalActionError.value = null), 4000);
}
const terminalHostRefs = ref<Record<string, TerminalHostInstance | null>>({});
const visibleTerminalSessionIds = ref<string[]>([]);

const activeTerminalSession = computed(() => shell.activeTerminalSession);
const activeTerminalCanClose = computed(
  () => activeTerminalSession.value.id !== DEFAULT_OPERATOR_TERMINAL_SESSION_ID,
);
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

const agentSessionId = computed(() => shell.terminalSessions.find((session) => session.role === 'agent')?.id ?? null);
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
    cwd: session.cwd,
    branch: session.branch,
    isolated: session.isolated,
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
  flushPendingOperatorTerminalCommand(pendingDeps(), sessionId);
  flushPendingAgentBackgroundTerminalCommand(pendingDeps(), sessionId);
}

function pendingDeps() {
  return {
    sessions: shell.terminalSessions,
    activeSessionId: shell.activeTerminalSessionId,
    hosts: terminalHostRefs.value,
    setVisibleSessionIds: (ids: string[]) => {
      visibleTerminalSessionIds.value = ids;
    },
  };
}

watch(pendingOperatorTerminalCommand, (command) => {
  if (!command) {
    return;
  }
  const session = focusSessionForPendingCommand({
    role: 'operator',
    sessions: shell.terminalSessions,
    activeSessionId: shell.activeTerminalSessionId,
    setActiveSessionId: (id) => shell.setActiveTerminalSession(id),
    setVisibleSessionIds: (ids) => {
      visibleTerminalSessionIds.value = ids;
    },
  });
  if (!session) {
    return;
  }
  requestAnimationFrame(() => {
    flushPendingOperatorTerminalCommand(pendingDeps(), session.id);
  });
});

watch(pendingAgentBackgroundCommand, (command) => {
  if (!command) {
    return;
  }
  const session = focusSessionForPendingCommand({
    role: 'agent',
    sessions: shell.terminalSessions,
    activeSessionId: shell.activeTerminalSessionId,
    setActiveSessionId: (id) => shell.setActiveTerminalSession(id),
    setVisibleSessionIds: (ids) => {
      visibleTerminalSessionIds.value = ids;
    },
  });
  if (!session) {
    return;
  }
  requestAnimationFrame(() => {
    flushPendingAgentBackgroundTerminalCommand(pendingDeps(), session.id);
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

function createTerminalSession(kind: 'bash' | 'zsh' | 'vaxon' = 'zsh'): void {
  closeNewTerminalMenu();
  if (kind === 'vaxon') {
    void shell.createVaxonTerminalSession().then((ok) => {
      if (!ok) {
        flashTerminalActionError('Could not start the vaxon terminal — check your connection and try again.');
      }
    });
    return;
  }
  void shell
    .createTerminalSession({
      role: 'operator',
      title: kind,
    })
    .then((created) => {
      if (!created) {
        flashTerminalActionError('Could not open a new terminal — check your connection and try again.');
      }
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
  if (!activeTerminalCanClose.value) {
    return;
  }
  killTerminalSession(activeTerminalSession.value.id);
}

function renameTerminalSession(sessionId: string, title: string): void {
  void shell.renameTerminalSession(sessionId, title).then((ok) => {
    if (!ok) {
      flashTerminalActionError('Could not rename that terminal tab — check your connection and try again.');
    }
  });
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

watch(
  () => shell.ideTerminalProblemsRevealToken,
  () => {
    bottomTab.value = 'problems';
  },
);

onMounted(() => {
  document.addEventListener('pointerdown', handleDocumentPointerDown, true);
});

onBeforeUnmount(() => {
  document.removeEventListener('pointerdown', handleDocumentPointerDown, true);
  if (terminalActionErrorTimer) {
    clearTimeout(terminalActionErrorTimer);
  }
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

      <p v-if="terminalActionError" class="terminal-tabbar__action-error" role="alert">
        {{ terminalActionError }}
      </p>

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
          <TerminalNewSessionMenu
            :open="showNewTerminalMenu"
            @create="createTerminalSession"
            @toggle="toggleNewTerminalMenu"
          />
          <button
            type="button"
            class="terminal-tabbar__action-button"
            :title="activeTerminalSession.role === 'agent' ? 'Split with zsh terminal' : 'Split terminal'"
            :aria-label="activeTerminalSession.role === 'agent' ? 'Split with zsh local terminal' : 'Split terminal'"
            @click="handleHeaderSplit"
          >
            <WorkbenchIcon name="split" class="terminal-tabbar__action" :size="16" />
          </button>
          <button
            type="button"
            class="terminal-tabbar__action-button"
            :title="activeTerminalCanClose ? 'Kill Terminal' : 'The default terminal stays available'"
            :aria-label="activeTerminalCanClose ? 'Kill Terminal' : 'Default terminal cannot be killed'"
            :disabled="!activeTerminalCanClose"
            @click="handleHeaderKill"
          >
            <WorkbenchIcon name="trash" class="terminal-tabbar__action" :size="16" />
          </button>
          <button
            type="button"
            class="terminal-tabbar__action-button"
            title="Clear terminal"
            aria-label="Clear terminal"
            @click="clearTerminalPanel"
          >
            <WorkbenchIcon name="clear" class="terminal-tabbar__action" :size="16" />
          </button>
          <button
            type="button"
            class="terminal-tabbar__action-button"
            :title="workbenchTerminalPanelTitle(true, terminalRunPhase)"
            :aria-label="workbenchTerminalPanelAriaLabel(true, terminalRunPhase)"
            @click="requestHideTerminalPanel"
          >
            <WorkbenchIcon name="chevron-down" class="terminal-tabbar__action" :size="16" />
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

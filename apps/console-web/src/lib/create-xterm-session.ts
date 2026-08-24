import { FitAddon } from '@xterm/addon-fit';
import { Terminal } from '@xterm/xterm';
import '@xterm/xterm/css/xterm.css';

import { buildTerminalWebSocketUrl } from './terminal-session-api';
import {
  mockupTerminalFontOptions,
  mockupXtermTheme,
} from './mockup-workbench-theme';
import { applyTerminalInputChunk, sanitizeTerminalInput } from './terminal-input';
import { attachTerminalPasteHandler } from './terminal-paste';
import {
  migrateTerminalScrollback,
  persistTerminalScrollback,
  restoreTerminalScrollback,
} from './terminal-scrollback';
import { attachTerminalWheelContainment } from './terminal-wheel-containment';

export interface TerminalContext {
  primarySignalId: string | null;
  runtimeConnected: boolean;
  runSummary: string | null;
  workspaceId: string | null;
  sessionId: string;
  sessionRole: string;
}

export interface XtermSessionOptions {
  readOnly?: boolean;
  variant?: 'default' | 'mockup';
}

export interface XtermSessionController {
  clearScreen: () => void;
  dispose: () => void;
  persistScrollback: () => void;
  setContext: (context: TerminalContext) => void;
  /** Replace the viewport with a Cursor-style agent shell mirror (no PTY). */
  writeMirrorSnapshot: (text: string) => void;
  /** Leave mirror mode and reconnect the agent PTY websocket. */
  exitMirrorMode: () => void;
  /** Send interactive keystrokes to an operator PTY. */
  writeInput: (data: string) => void;
  /** Execute a complete command in a read-only agent PTY. */
  runCommand: (command: string) => void;
}

interface TerminalServerMessage {
  type: string;
  data?: string;
  message?: string;
  workspace_id?: string;
  workspace_root?: string;
}

/** Transient WS drops happen on server restarts/network blips; mirror the chat-stream backoff. */
export const TERMINAL_RECONNECT_MAX_ATTEMPTS = 6;
export const TERMINAL_RECONNECT_BASE_MS = 500;
/**
 * Close codes the terminal WebSocket route sends for conditions that will never
 * succeed on retry (see services/control-plane/app/terminal/session_handler.py,
 * WorkspaceRootError -> code=4400). Reconnecting against these just wastes the
 * backoff window before failing the same way every time.
 */
const TERMINAL_NON_RETRYABLE_CLOSE_CODES = new Set([4400]);

function sendResize(socket: WebSocket, terminal: Terminal): void {
  if (socket.readyState !== WebSocket.OPEN) {
    return;
  }

  socket.send(
    JSON.stringify({
      type: 'resize',
      cols: terminal.cols,
      rows: terminal.rows,
    }),
  );
}

export async function createXtermSession(
  container: HTMLElement,
  options: XtermSessionOptions = {},
): Promise<XtermSessionController> {
  const useMockupTheme = options.variant === 'mockup';
  const readOnly = Boolean(options.readOnly);
  const terminal = new Terminal({
    theme: useMockupTheme
      ? mockupXtermTheme
      : {
          ...mockupXtermTheme,
          // Slightly deeper ink for non-mockup hosts while keeping full ANSI.
          background: '#050f18',
        },
    fontSize: useMockupTheme ? mockupTerminalFontOptions.fontSize : 14,
    lineHeight: useMockupTheme ? mockupTerminalFontOptions.lineHeight : 1.3,
    fontFamily: useMockupTheme
      ? mockupTerminalFontOptions.fontFamily
      : mockupTerminalFontOptions.fontFamily,
    cursorBlink: !readOnly,
    cursorStyle: readOnly ? 'underline' : 'block',
    cursorWidth: 2,
    convertEol: true,
    disableStdin: readOnly,
    allowTransparency: false,
    macOptionIsMeta: true,
    rightClickSelectsWord: true,
    // Agent mirrors can contain complete build/test logs. Keep enough browser
    // scrollback that full server output remains reviewable instead of silently
    // falling back to xterm's 1,000-line default.
    scrollback: 100_000,
  });
  const fitAddon = new FitAddon();
  terminal.loadAddon(fitAddon);
  terminal.open(container);
  fitAddon.fit();
  const detachTerminalWheelContainment = attachTerminalWheelContainment(container);

  let attachedWorkspaceId: string | null = null;
  let attachedSessionId = 'terminal-operator';
  let attachedSessionRole = 'operator';
  let socket: WebSocket | null = null;
  let inputDisposable: { dispose: () => void } | null = null;
  let pasteDisposable: (() => void) | null = null;
  let pendingInputLine = '';
  let pendingAgentCommand: string | null = null;
  let mirrorMode = false;
  let lastMirrorText = '';
  let socketSendInput: ((data: string) => void) | null = null;
  let reconnectAttempts = 0;
  let reconnectTargetKey: string | null = null;
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null;

  const clearReconnectTimer = (): void => {
    if (reconnectTimer) {
      clearTimeout(reconnectTimer);
      reconnectTimer = null;
    }
  };

  const clearScreen = (): void => {
    terminal.clear();
  };

  const persistAttachedScrollback = (): void => {
    if (!attachedWorkspaceId) {
      return;
    }
    persistTerminalScrollback(attachedWorkspaceId, terminal, attachedSessionId);
  };

  const writeStatus = (message: string): void => {
    terminal.writeln('');
    terminal.writeln(message);
  };

  let connectGeneration = 0;

  const disposeSocket = (): void => {
    clearReconnectTimer();
    inputDisposable?.dispose();
    inputDisposable = null;
    pasteDisposable?.();
    pasteDisposable = null;
    if (!socket) {
      return;
    }

    const activeSocket = socket;
    socket = null;
    activeSocket.onopen = null;
    activeSocket.onmessage = null;
    activeSocket.onerror = null;
    activeSocket.onclose = null;

    if (activeSocket.readyState === WebSocket.OPEN) {
      activeSocket.close();
    }
  };

  const writeMirrorSnapshot = (text: string): void => {
    mirrorMode = true;
    disposeSocket();
    const normalized = text.replace(/\n/g, '\r\n');
    if (lastMirrorText && normalized.startsWith(lastMirrorText)) {
      const delta = normalized.slice(lastMirrorText.length);
      if (delta) {
        terminal.write(delta);
      }
      lastMirrorText = normalized;
      return;
    }
    terminal.reset();
    terminal.write(normalized);
    lastMirrorText = normalized;
  };

  const openSocket = (
    workspaceId: string,
    sessionId: string,
    sessionRole: string,
  ): void => {
    const generation = ++connectGeneration;
    const nextSocket = new WebSocket(
      buildTerminalWebSocketUrl(workspaceId, {
        sessionId,
        role: sessionRole,
      }),
    );
    socket = nextSocket;

    nextSocket.onopen = () => {
      if (generation !== connectGeneration || socket !== nextSocket) {
        return;
      }

      reconnectAttempts = 0;
      fitAddon.fit();
      sendResize(nextSocket, terminal);

      const sendInput = (data: string): void => {
        if (socket !== nextSocket || nextSocket.readyState !== WebSocket.OPEN) {
          return;
        }

        const sanitized = sanitizeTerminalInput(data);
        const inputResult = applyTerminalInputChunk(pendingInputLine, sanitized);
        pendingInputLine = inputResult.nextInputLine;
        if (inputResult.shouldClear) {
          clearScreen();
        }

        nextSocket.send(JSON.stringify({ type: 'input', data: sanitized }));
      };
      socketSendInput = sendInput;

      // Agent tabs stay keyboard-read-only; explicit run_command messages still work.
      // Operator tabs accept interactive typing + paste.
      if (sessionRole !== 'agent') {
        pasteDisposable = attachTerminalPasteHandler(container, sendInput);
        inputDisposable = terminal.onData((data) => {
          sendInput(data);
        });
      }
      if (sessionRole === 'agent' && pendingAgentCommand) {
        nextSocket.send(
          JSON.stringify({
            type: 'run_command',
            command: pendingAgentCommand,
          }),
        );
        pendingAgentCommand = null;
      }
    };

    nextSocket.onmessage = (event) => {
      if (generation !== connectGeneration || socket !== nextSocket) {
        return;
      }

      let message: TerminalServerMessage;
      try {
        message = JSON.parse(String(event.data)) as TerminalServerMessage;
      } catch {
        terminal.write(String(event.data));
        return;
      }

      if (message.type === 'output' && typeof message.data === 'string') {
        terminal.write(message.data);
        return;
      }

      if (message.type === 'ready') {
        return;
      }

      if (message.type === 'error' && message.message) {
        writeStatus(`[terminal] ${message.message}`);
        return;
      }

      if (message.type === 'closed') {
        return;
      }
    };

    nextSocket.onerror = () => {
      if (generation !== connectGeneration || socket !== nextSocket) {
        return;
      }
    };

    nextSocket.onclose = (event) => {
      // disposeSocket() nulls this handler before closing intentionally (dispose,
      // explicit re-attach, mirror mode), so reaching here means the server or
      // network dropped the connection out from under us — reconnect with backoff
      // instead of leaving the terminal silently dead.
      if (generation !== connectGeneration || attachedWorkspaceId !== workspaceId || socket !== nextSocket) {
        return;
      }
      socket = null;
      socketSendInput = null;

      if (TERMINAL_NON_RETRYABLE_CLOSE_CODES.has(event.code)) {
        writeStatus('[terminal] this workspace/session is no longer available. Close and reopen this tab.');
        return;
      }

      if (reconnectAttempts >= TERMINAL_RECONNECT_MAX_ATTEMPTS) {
        writeStatus(
          `[terminal] disconnected after ${TERMINAL_RECONNECT_MAX_ATTEMPTS} reconnect attempts. Close and reopen this tab to reconnect.`,
        );
        return;
      }

      const delayMs = TERMINAL_RECONNECT_BASE_MS * 2 ** reconnectAttempts;
      reconnectAttempts += 1;
      if (reconnectAttempts === 1) {
        writeStatus('[terminal] connection lost — reconnecting…');
      }
      clearReconnectTimer();
      reconnectTimer = setTimeout(() => {
        reconnectTimer = null;
        if (attachedWorkspaceId === workspaceId) {
          openSocket(workspaceId, sessionId, sessionRole);
        }
      }, delayMs);
    };
  };

  const attachWorkspace = (
    workspaceId: string | null,
    sessionId = 'terminal-operator',
    sessionRole = 'operator',
  ): void => {
    if (
      workspaceId === attachedWorkspaceId &&
      sessionId === attachedSessionId &&
      socket &&
      (socket.readyState === WebSocket.CONNECTING || socket.readyState === WebSocket.OPEN)
    ) {
      return;
    }

    if (attachedWorkspaceId) {
      persistAttachedScrollback();
    }
    disposeSocket();
    pendingInputLine = '';
    socketSendInput = null;
    attachedWorkspaceId = workspaceId;
    attachedSessionId = sessionId;
    attachedSessionRole = sessionRole;

    const targetKey = `${workspaceId ?? ''}::${sessionId}::${sessionRole}`;
    if (targetKey !== reconnectTargetKey) {
      reconnectAttempts = 0;
      reconnectTargetKey = targetKey;
    }

    if (!workspaceId) {
      return;
    }

    migrateTerminalScrollback(workspaceId, sessionId);
    terminal.clear();
    const restoredScrollback = restoreTerminalScrollback(workspaceId, terminal, sessionId);
    if (restoredScrollback) {
      terminal.write('\r\n');
    }

    openSocket(workspaceId, sessionId, sessionRole);
  };

  const onResize = (): void => {
    fitAddon.fit();
    if (socket) {
      sendResize(socket, terminal);
    }
  };
  window.addEventListener('resize', onResize);
  const resizeObserver = new ResizeObserver(() => {
    onResize();
  });
  resizeObserver.observe(container);

  return {
    clearScreen,
    dispose() {
      persistAttachedScrollback();
      detachTerminalWheelContainment();
      window.removeEventListener('resize', onResize);
      resizeObserver.disconnect();
      disposeSocket();
      terminal.dispose();
    },
    persistScrollback: persistAttachedScrollback,
    setContext(context: TerminalContext) {
      if (mirrorMode && context.sessionRole === 'agent') {
        attachedWorkspaceId = context.workspaceId;
        attachedSessionId = context.sessionId;
        attachedSessionRole = context.sessionRole;
        return;
      }
      if (
        context.workspaceId !== attachedWorkspaceId ||
        context.sessionId !== attachedSessionId ||
        context.sessionRole !== attachedSessionRole
      ) {
        mirrorMode = false;
        attachWorkspace(context.workspaceId, context.sessionId, context.sessionRole);
      }
    },
    writeMirrorSnapshot,
    writeInput(data: string) {
      if (mirrorMode) {
        return;
      }
      if (readOnly) {
        return;
      }
      socketSendInput?.(data);
    },
    runCommand(command: string) {
      if (mirrorMode || attachedSessionRole !== 'agent') {
        return;
      }
      const trimmed = command.trim();
      if (!trimmed) {
        return;
      }
      if (!socket || socket.readyState !== WebSocket.OPEN) {
        pendingAgentCommand = trimmed;
        return;
      }
      socket.send(JSON.stringify({ type: 'run_command', command: trimmed }));
    },
    exitMirrorMode() {
      if (!mirrorMode) {
        return;
      }
      mirrorMode = false;
      lastMirrorText = '';
      const workspaceId = attachedWorkspaceId;
      const sessionId = attachedSessionId;
      const sessionRole = attachedSessionRole;
      // Force attachWorkspace to reconnect even if ids are unchanged.
      attachedWorkspaceId = null;
      if (workspaceId) {
        attachWorkspace(workspaceId, sessionId, sessionRole);
      }
    },
  };
}

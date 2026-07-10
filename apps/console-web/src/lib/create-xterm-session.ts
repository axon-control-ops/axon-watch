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
}

interface TerminalServerMessage {
  type: string;
  data?: string;
  message?: string;
  workspace_id?: string;
  workspace_root?: string;
}

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
          background: '#050a12',
          foreground: '#8fa4b8',
          cursor: '#edf8ff',
          brightBlack: '#5f7388',
          brightCyan: '#00f2ff',
        },
    fontSize: useMockupTheme ? mockupTerminalFontOptions.fontSize : 15,
    lineHeight: useMockupTheme ? mockupTerminalFontOptions.lineHeight : 1.25,
    fontFamily: useMockupTheme
      ? mockupTerminalFontOptions.fontFamily
      : 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
    cursorBlink: !readOnly,
    convertEol: true,
    disableStdin: readOnly,
  });
  const fitAddon = new FitAddon();
  terminal.loadAddon(fitAddon);
  terminal.open(container);
  fitAddon.fit();

  let attachedWorkspaceId: string | null = null;
  let attachedSessionId = 'terminal-operator';
  let attachedSessionRole = 'operator';
  let socket: WebSocket | null = null;
  let inputDisposable: { dispose: () => void } | null = null;
  let pasteDisposable: (() => void) | null = null;
  let pendingInputLine = '';

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

    const generation = ++connectGeneration;
    if (attachedWorkspaceId) {
      persistAttachedScrollback();
    }
    disposeSocket();
    pendingInputLine = '';
    attachedWorkspaceId = workspaceId;
    attachedSessionId = sessionId;
    attachedSessionRole = sessionRole;

    if (!workspaceId) {
      return;
    }

    migrateTerminalScrollback(workspaceId, sessionId);
    terminal.clear();
    const restoredScrollback = restoreTerminalScrollback(workspaceId, terminal, sessionId);
    if (restoredScrollback) {
      terminal.write('\r\n');
    }

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

      fitAddon.fit();
      sendResize(nextSocket, terminal);

      if (sessionRole === 'agent') {
        return;
      }

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

      pasteDisposable = attachTerminalPasteHandler(container, sendInput);

      inputDisposable = terminal.onData((data) => {
        sendInput(data);
      });
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

    nextSocket.onclose = () => {
      if (generation !== connectGeneration || attachedWorkspaceId !== workspaceId) {
        return;
      }
    };
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
      window.removeEventListener('resize', onResize);
      resizeObserver.disconnect();
      disposeSocket();
      terminal.dispose();
    },
    persistScrollback: persistAttachedScrollback,
    setContext(context: TerminalContext) {
      if (
        context.workspaceId !== attachedWorkspaceId ||
        context.sessionId !== attachedSessionId ||
        context.sessionRole !== attachedSessionRole
      ) {
        attachWorkspace(context.workspaceId, context.sessionId, context.sessionRole);
      }
    },
  };
}

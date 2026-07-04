import { FitAddon } from '@xterm/addon-fit';
import { Terminal } from '@xterm/xterm';
import '@xterm/xterm/css/xterm.css';

import { buildTerminalWebSocketUrl } from './terminal-session-api';

export interface TerminalContext {
  primarySignalId: string | null;
  runtimeConnected: boolean;
  runSummary: string | null;
  workspaceId: string | null;
}

export interface XtermSessionController {
  dispose: () => void;
  setContext: (context: TerminalContext) => void;
}

interface TerminalServerMessage {
  type: string;
  data?: string;
  message?: string;
  workspace_id?: string;
  workspace_root?: string;
}

function formatContext(context: TerminalContext): string {
  return [
    `workspace=${context.workspaceId ?? 'none'}`,
    `run=${context.runSummary ?? 'none'}`,
    `signal=${context.primarySignalId ?? 'none'}`,
    `watch=${context.runtimeConnected ? 'connected' : 'disconnected'}`,
  ].join(' ');
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

export async function createXtermSession(container: HTMLElement): Promise<XtermSessionController> {
  const terminal = new Terminal({
    theme: {
      background: '#0f172a',
      foreground: '#dbe4ff',
      cursor: '#38bdf8',
    },
    fontSize: 15,
    lineHeight: 1.25,
    fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
    cursorBlink: true,
    convertEol: true,
  });
  const fitAddon = new FitAddon();
  terminal.loadAddon(fitAddon);
  terminal.open(container);
  fitAddon.fit();

  let currentContext: TerminalContext = {
    workspaceId: null,
    runSummary: null,
    primarySignalId: null,
    runtimeConnected: false,
  };
  let attachedWorkspaceId: string | null = null;
  let socket: WebSocket | null = null;
  let inputDisposable: { dispose: () => void } | null = null;

  const writeStatus = (message: string): void => {
    terminal.writeln('');
    terminal.writeln(message);
  };

  const disposeSocket = (): void => {
    inputDisposable?.dispose();
    inputDisposable = null;
    if (socket) {
      socket.onopen = null;
      socket.onmessage = null;
      socket.onerror = null;
      socket.onclose = null;
      if (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING) {
        socket.close();
      }
    }
    socket = null;
  };

  const attachWorkspace = (workspaceId: string | null): void => {
    disposeSocket();
    attachedWorkspaceId = workspaceId;

    if (!workspaceId) {
      writeStatus('[terminal] Select a workspace to attach a backend shell.');
      return;
    }

    writeStatus(`[terminal] Connecting backend PTY for ${workspaceId}...`);
    socket = new WebSocket(buildTerminalWebSocketUrl(workspaceId));

    socket.onopen = () => {
      fitAddon.fit();
      sendResize(socket as WebSocket, terminal);
      inputDisposable = terminal.onData((data) => {
        if (socket?.readyState !== WebSocket.OPEN) {
          return;
        }
        socket.send(JSON.stringify({ type: 'input', data }));
      });
    };

    socket.onmessage = (event) => {
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
        writeStatus(
          `[attached] workspace=${message.workspace_id ?? workspaceId} root=${message.workspace_root ?? 'unknown'}`,
        );
        return;
      }

      if (message.type === 'error' && message.message) {
        writeStatus(`[terminal] ${message.message}`);
        return;
      }

      if (message.type === 'closed') {
        writeStatus('[terminal] backend session closed.');
      }
    };

    socket.onerror = () => {
      writeStatus('[terminal] backend connection error.');
    };

    socket.onclose = () => {
      if (attachedWorkspaceId === workspaceId) {
        writeStatus('[terminal] disconnected from backend shell.');
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
    dispose() {
      window.removeEventListener('resize', onResize);
      resizeObserver.disconnect();
      disposeSocket();
      terminal.dispose();
    },
    setContext(context: TerminalContext) {
      const previous = currentContext;
      currentContext = context;

      if (context.workspaceId !== attachedWorkspaceId) {
        attachWorkspace(context.workspaceId);
        return;
      }

      if (formatContext(context) !== formatContext(previous)) {
        writeStatus(`[context] ${formatContext(context)}`);
      }
    },
  };
}

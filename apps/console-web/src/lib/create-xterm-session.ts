import { FitAddon } from '@xterm/addon-fit';
import { Terminal } from '@xterm/xterm';
import '@xterm/xterm/css/xterm.css';

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

function formatContext(context: TerminalContext): string {
  return [
    `workspace=${context.workspaceId ?? 'none'}`,
    `run=${context.runSummary ?? 'none'}`,
    `signal=${context.primarySignalId ?? 'none'}`,
    `watch=${context.runtimeConnected ? 'connected' : 'disconnected'}`,
  ].join(' ');
}

export async function createXtermSession(container: HTMLElement): Promise<XtermSessionController> {
  const terminal = new Terminal({
    theme: {
      background: '#0f172a',
      foreground: '#dbe4ff',
      cursor: '#38bdf8',
    },
    fontSize: 13,
    fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
    cursorBlink: true,
    convertEol: true,
  });
  const fitAddon = new FitAddon();
  terminal.loadAddon(fitAddon);
  terminal.open(container);
  fitAddon.fit();

  terminal.writeln('Axon-X terminal host ready.');
  terminal.writeln('Type "help" for shell-state commands.');

  let currentContext: TerminalContext = {
    workspaceId: null,
    runSummary: null,
    primarySignalId: null,
    runtimeConnected: false,
  };
  let inputBuffer = '';

  const prompt = (): void => {
    terminal.write('\r\naxon-x> ');
  };

  const handleCommand = (command: string): void => {
    const trimmed = command.trim();
    if (!trimmed) {
      prompt();
      return;
    }
    if (trimmed === 'clear') {
      terminal.clear();
      terminal.writeln('Axon-X terminal host ready.');
      terminal.writeln('Type "help" for shell-state commands.');
      prompt();
      return;
    }

    if (trimmed === 'help') {
      terminal.writeln('');
      terminal.writeln('help       show available commands');
      terminal.writeln('context    show current shell attachment state');
      terminal.writeln('workspace  show selected workspace');
      terminal.writeln('run        show primary run summary');
      terminal.writeln('signal     show primary signal');
      terminal.writeln('clear      clear the terminal');
      prompt();
      return;
    }

    if (trimmed === 'context') {
      terminal.writeln('');
      terminal.writeln(formatContext(currentContext));
      prompt();
      return;
    }

    if (trimmed === 'workspace') {
      terminal.writeln('');
      terminal.writeln(currentContext.workspaceId ?? 'No workspace selected.');
      prompt();
      return;
    }

    if (trimmed === 'run') {
      terminal.writeln('');
      terminal.writeln(currentContext.runSummary ?? 'No active run attached.');
      prompt();
      return;
    }

    if (trimmed === 'signal') {
      terminal.writeln('');
      terminal.writeln(currentContext.primarySignalId ?? 'No signal attached.');
      prompt();
      return;
    }

    terminal.writeln('');
    terminal.writeln(`Unknown command: ${trimmed}`);
    terminal.writeln('Try: help');
    prompt();
  };

  terminal.onData((data) => {
    if (data === '\r') {
      handleCommand(inputBuffer);
      inputBuffer = '';
      return;
    }
    if (data === '\u007F') {
      if (inputBuffer.length > 0) {
        inputBuffer = inputBuffer.slice(0, -1);
        terminal.write('\b \b');
      }
      return;
    }
    if (data >= ' ') {
      inputBuffer += data;
      terminal.write(data);
    }
  });
  prompt();

  const onResize = (): void => {
    fitAddon.fit();
  };
  window.addEventListener('resize', onResize);
  const resizeObserver = new ResizeObserver(() => {
    fitAddon.fit();
  });
  resizeObserver.observe(container);

  return {
    dispose() {
      window.removeEventListener('resize', onResize);
      resizeObserver.disconnect();
      terminal.dispose();
    },
    setContext(context: TerminalContext) {
      const nextFormatted = formatContext(context);
      const currentFormatted = formatContext(currentContext);
      currentContext = context;
      if (nextFormatted !== currentFormatted) {
        terminal.writeln('');
        terminal.writeln(`[attached] ${nextFormatted}`);
        prompt();
      }
    },
  };
}

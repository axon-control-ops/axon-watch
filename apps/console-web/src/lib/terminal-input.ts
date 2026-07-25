/** Strip xterm bracketed-paste markers before forwarding keystrokes to the PTY. */

export function sanitizeTerminalInput(data: string): string {
  return data.replace(/\x1b\[200~/g, '').replace(/\x1b\[201~/g, '');
}

/** Detect operator clear intent from PTY keystrokes before forwarding to the shell. */

export function applyTerminalInputChunk(
  inputLine: string,
  data: string,
): { nextInputLine: string; shouldClear: boolean } {
  let line = inputLine;
  let shouldClear = false;
  const sanitized = sanitizeTerminalInput(data);

  for (const char of sanitized) {
    if (char === '\x0c') {
      shouldClear = true;
      continue;
    }

    if (char === '\r' || char === '\n') {
      const command = line.trim();
      if (command === 'clear' || command === 'reset') {
        shouldClear = true;
      }
      line = '';
      continue;
    }

    if (char === '\x7f' || char === '\b') {
      line = line.slice(0, -1);
      continue;
    }

    if (char >= ' ' || char === '\t') {
      line += char;
    }
  }

  return { nextInputLine: line, shouldClear };
}

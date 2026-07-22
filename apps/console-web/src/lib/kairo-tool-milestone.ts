/** Human-readable operator copy for agent :::tool milestones. */

const READ_RE = /^read\s+(.+)$/i;
const EDIT_RE = /^edit(?:\s+failed)?\s+(.+)$/i;
const SHELL_RE = /^(?:shell|run|bash)\s+(.+)$/i;
const RESEARCH_RE = /^(?:axon\s+)?research(?:\s+search)?\s+(.+)$/i;

/** Meta/docs agents open for orientation — not worth interrupting a live run with. */
const AMBIENT_DOC_RE =
  /^(operations|readme|agents|claude|contributing|changelog|license)(?:\.(md|txt|rst))?$/i;

export type ToolMilestoneSpeakOptions = {
  operatorPrompt?: string | null;
  taskSummary?: string | null;
};

function shortName(path: string): string {
  const normalized = path.trim().replace(/\\/g, '/');
  if (!normalized) {
    return 'that file';
  }
  const parts = normalized.split('/');
  const base = parts[parts.length - 1]?.trim();
  return base || normalized;
}

function shortCommand(command: string): string {
  const text = command.replace(/\s+/g, ' ').trim();
  if (!text) {
    return 'that command';
  }
  if (text.length <= 48) {
    return text;
  }
  return `${text.slice(0, 45).trim()}…`;
}

function cleanPrompt(prompt: string | null | undefined): string {
  return String(prompt ?? '')
    .replace(/\s+/g, ' ')
    .trim();
}

function promptSnippet(prompt: string, max = 42): string {
  if (!prompt) {
    return '';
  }
  if (prompt.length <= max) {
    return prompt;
  }
  return `${prompt.slice(0, max - 1).trim()}…`;
}

function isAmbientDoc(fileName: string): boolean {
  return AMBIENT_DOC_RE.test(fileName.trim());
}

function taskHint(options?: ToolMilestoneSpeakOptions): string {
  const summary = cleanPrompt(options?.taskSummary);
  if (summary && !/^(thinking|done|failed)/i.test(summary)) {
    return promptSnippet(summary, 56);
  }
  return promptSnippet(cleanPrompt(options?.operatorPrompt), 56);
}

/**
 * Turn a raw :::tool header into a short spoken line.
 * Returns empty string when the tool is ambient noise (skip speaking).
 */
export function toolMilestoneSpeakLine(
  toolLabel: string,
  options?: ToolMilestoneSpeakOptions,
): string {
  const raw = toolLabel.trim();
  if (!raw) {
    return '';
  }

  const hint = taskHint(options);

  const readMatch = raw.match(READ_RE);
  if (readMatch?.[1]) {
    const name = shortName(readMatch[1]);
    if (isAmbientDoc(name)) {
      // Orientation reads — live thinking already covers intent.
      return '';
    }
    if (hint) {
      return `Checking ${name} for: ${hint}`;
    }
    return `Checking ${name}.`;
  }

  const editMatch = raw.match(EDIT_RE);
  if (editMatch?.[1]) {
    const name = shortName(editMatch[1]);
    if (hint) {
      return `Updating ${name} — ${hint}`;
    }
    return `Updating ${name}.`;
  }

  const shellMatch = raw.match(SHELL_RE);
  if (shellMatch?.[1]) {
    const command = shortCommand(shellMatch[1]);
    const lowered = command.toLowerCase();
    if (/\b(eas\s+update|ota|expo\s+publish)\b/.test(lowered)) {
      return hint
        ? `Running the production OTA — ${hint}`
        : 'Running the production OTA in the terminal.';
    }
    if (/\b(poll|watch|tail|sleep)\b/.test(lowered)) {
      return hint
        ? `Still monitoring — ${hint}`
        : `Monitoring terminal output from ${command}.`;
    }
    return hint
      ? `Running ${command} — ${hint}`
      : `Running ${command} in the terminal.`;
  }

  const researchMatch = raw.match(RESEARCH_RE);
  if (researchMatch?.[1]) {
    const query = researchMatch[1].trim();
    return query ? `Searching for ${query}.` : 'Running a research search.';
  }

  const lowered = raw.toLowerCase();
  if (lowered.startsWith('create')) {
    return hint ? `Drafting a plan for: ${hint}` : 'Putting together a plan for this.';
  }

  const words = raw.split(/\s+/);
  if (words.length >= 2) {
    const action = words[0].charAt(0).toUpperCase() + words[0].slice(1);
    const target = shortName(words.slice(1).join(' '));
    return hint ? `${action} ${target} — ${hint}` : `${action} — working on ${target}.`;
  }

  return hint ? `Working on ${raw} — ${hint}` : `Working on ${raw}.`;
}

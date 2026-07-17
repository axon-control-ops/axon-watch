/** Human-readable operator copy for agent :::tool milestones. */

const READ_RE = /^read\s+(.+)$/i;
const EDIT_RE = /^edit(?:\s+failed)?\s+(.+)$/i;
const SHELL_RE = /^(?:shell|run|bash)\s+(.+)$/i;
const RESEARCH_RE = /^(?:axon\s+)?research(?:\s+search)?\s+(.+)$/i;

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

export function toolMilestoneSpeakLine(toolLabel: string): string {
  const raw = toolLabel.trim();
  if (!raw) {
    return '';
  }

  const readMatch = raw.match(READ_RE);
  if (readMatch?.[1]) {
    return `I'm opening ${shortName(readMatch[1])} to review what we're working with.`;
  }

  const editMatch = raw.match(EDIT_RE);
  if (editMatch?.[1]) {
    return `I'm updating ${shortName(editMatch[1])}.`;
  }

  const shellMatch = raw.match(SHELL_RE);
  if (shellMatch?.[1]) {
    return `I'm running ${shortCommand(shellMatch[1])} in the terminal.`;
  }

  const researchMatch = raw.match(RESEARCH_RE);
  if (researchMatch?.[1]) {
    const query = researchMatch[1].trim();
    return query ? `I'm searching for ${query}.` : "I'm running a research search.";
  }

  const lowered = raw.toLowerCase();
  if (lowered.startsWith('create')) {
    return "I'm putting together a plan for this.";
  }

  const words = raw.split(/\s+/);
  if (words.length >= 2) {
    const action = words[0].charAt(0).toUpperCase() + words[0].slice(1);
    return `${action} — working on ${shortName(words.slice(1).join(' '))}.`;
  }

  return `Working on ${raw}.`;
}

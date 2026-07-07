/** Parse block-annotated agent transcripts (:::thinking / :::edit / :::tool / :::terminal). */

export type AgentTranscriptSegment =
  | { kind: 'text'; text: string }
  | { kind: 'thinking'; text: string; open: boolean }
  | {
      kind: 'edit';
      path: string;
      added: number;
      removed: number;
      diff: string;
      open: boolean;
    }
  | { kind: 'tool'; label: string }
  | { kind: 'research'; query: string; items: ResearchTranscriptItem[]; open: boolean }
  | { kind: 'terminal'; command: string; output: string; open: boolean };

export type ResearchTranscriptItem = {
  title: string;
  url: string;
  snippet: string;
};

const EDIT_HEADER_RE = /^:::edit\s+(.+?)\s+\+(\d+)\s+-(\d+)\s*$/;
const TOOL_HEADER_RE = /^:::tool\s+(.+)$/;
const RESEARCH_HEADER_RE = /^:::research\s+(.+)$/;
const RESEARCH_ITEM_RE = /^-\s+(.+?)\s+\|\s+(\S+)\s*$/;
const TERMINAL_HEADER_RE = /^:::terminal\s+(.+)$/;

export function agentContentHasTranscriptBlocks(content: string): boolean {
  return /^:::(thinking|edit|tool|terminal|research)\b/m.test(content);
}

export function parseAgentTranscriptBlocks(content: string): AgentTranscriptSegment[] {
  const segments: AgentTranscriptSegment[] = [];
  const lines = content.split('\n');
  let textBuffer: string[] = [];
  let index = 0;

  function flushText(): void {
    const text = textBuffer.join('\n').replace(/^\n+|\n+$/g, '');
    if (text.trim()) {
      segments.push({ kind: 'text', text });
    }
    textBuffer = [];
  }

  while (index < lines.length) {
    const line = lines[index];

    if (line.trimEnd() === ':::thinking') {
      flushText();
      const body: string[] = [];
      let closed = false;
      index += 1;
      while (index < lines.length) {
        if (lines[index].trimEnd() === ':::') {
          closed = true;
          index += 1;
          break;
        }
        body.push(lines[index]);
        index += 1;
      }
      segments.push({
        kind: 'thinking',
        text: body.join('\n').replace(/^\n+|\n+$/g, ''),
        open: !closed,
      });
      continue;
    }

    const editMatch = line.match(EDIT_HEADER_RE);
    if (editMatch) {
      flushText();
      const body: string[] = [];
      let closed = false;
      index += 1;
      while (index < lines.length) {
        if (lines[index].trimEnd() === ':::') {
          closed = true;
          index += 1;
          break;
        }
        body.push(lines[index]);
        index += 1;
      }
      segments.push({
        kind: 'edit',
        path: editMatch[1],
        added: Number(editMatch[2]),
        removed: Number(editMatch[3]),
        diff: body.join('\n').replace(/^\n+|\n+$/g, ''),
        open: !closed,
      });
      continue;
    }

    const toolMatch = line.match(TOOL_HEADER_RE);
    if (toolMatch) {
      flushText();
      segments.push({ kind: 'tool', label: toolMatch[1].trim() });
      index += 1;
      continue;
    }

    const researchMatch = line.match(RESEARCH_HEADER_RE);
    if (researchMatch) {
      flushText();
      const items: ResearchTranscriptItem[] = [];
      let closed = false;
      let pendingSnippet: string[] = [];
      index += 1;

      function flushSnippet(): void {
        if (items.length === 0 || pendingSnippet.length === 0) {
          pendingSnippet = [];
          return;
        }
        const last = items[items.length - 1];
        last.snippet = pendingSnippet.join('\n').trim();
        pendingSnippet = [];
      }

      while (index < lines.length) {
        const current = lines[index];
        if (current.trimEnd() === ':::') {
          closed = true;
          flushSnippet();
          index += 1;
          break;
        }

        const itemMatch = current.match(RESEARCH_ITEM_RE);
        if (itemMatch) {
          flushSnippet();
          items.push({
            title: itemMatch[1].trim(),
            url: itemMatch[2].trim(),
            snippet: '',
          });
          index += 1;
          continue;
        }

        if (items.length > 0) {
          pendingSnippet.push(current);
        }
        index += 1;
      }

      segments.push({
        kind: 'research',
        query: researchMatch[1].trim(),
        items,
        open: !closed,
      });
      continue;
    }

    const terminalMatch = line.match(TERMINAL_HEADER_RE);
    if (terminalMatch) {
      flushText();
      const body: string[] = [];
      let closed = false;
      index += 1;
      while (index < lines.length) {
        if (lines[index].trimEnd() === ':::') {
          closed = true;
          index += 1;
          break;
        }
        body.push(lines[index]);
        index += 1;
      }
      segments.push({
        kind: 'terminal',
        command: terminalMatch[1].trim(),
        output: body.join('\n').replace(/^\n+|\n+$/g, ''),
        open: !closed,
      });
      continue;
    }

    textBuffer.push(line);
    index += 1;
  }

  flushText();
  return segments;
}

export type DiffLineTone = 'add' | 'remove' | 'meta' | 'context';

export function diffLineTone(line: string): DiffLineTone {
  if (line.startsWith('+++') || line.startsWith('---') || line.startsWith('@@')) {
    return 'meta';
  }
  if (line.startsWith('+')) {
    return 'add';
  }
  if (line.startsWith('-')) {
    return 'remove';
  }
  return 'context';
}

export function thinkingPreview(text: string, maxLength = 90): string {
  const flattened = text.replace(/\s+/g, ' ').trim();
  if (flattened.length <= maxLength) {
    return flattened;
  }
  return `${flattened.slice(0, maxLength - 1).trimEnd()}…`;
}

/** Workspace-relative paths mentioned in completed edit blocks. */
export function editedFilePathsFromTranscript(content: string): string[] {
  const paths: string[] = [];
  for (const segment of parseAgentTranscriptBlocks(content)) {
    if (segment.kind !== 'edit' || segment.open) {
      continue;
    }
    const normalized = segment.path.trim().replace(/\\/g, '/');
    if (!normalized || normalized.startsWith('/')) {
      paths.push(fileBaseName(normalized));
      continue;
    }
    paths.push(normalized);
  }
  return [...new Set(paths)];
}

function fileBaseName(path: string): string {
  const parts = path.split('/');
  return parts[parts.length - 1] || path;
}

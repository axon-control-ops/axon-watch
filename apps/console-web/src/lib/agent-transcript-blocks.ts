/** Parse block-annotated agent transcripts (:::thinking / :::edit / :::tool). */

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
  | { kind: 'tool'; label: string };

const EDIT_HEADER_RE = /^:::edit\s+(.+?)\s+\+(\d+)\s+-(\d+)\s*$/;
const TOOL_HEADER_RE = /^:::tool\s+(.+)$/;

export function agentContentHasTranscriptBlocks(content: string): boolean {
  return /^:::(thinking|edit|tool)\b/m.test(content);
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

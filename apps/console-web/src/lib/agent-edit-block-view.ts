import { languageForFilePath } from './workspace-file-language';
import { extractProposedFileContentFromDiff, isMarkdownAgentEditPath } from './ide-agent-edit-review';
import { normalizeEditedFilePath } from './agent-transcript-blocks';

const MAX_MARKDOWN_PREVIEW_CHARS = 1200;
const MAX_DIFF_PREVIEW_LINES = 24;

export const AGENT_EDIT_BLOCK_DEFAULT_EXPANDED = true;

export type AgentEditDiffLine = {
  text: string;
  tone: 'add' | 'remove' | 'meta' | 'context';
};

export type AgentEditBlockView =
  | {
      mode: 'markdown';
      path: string;
      previewMarkdown: string;
      truncated: boolean;
      totalLines: number;
    }
  | {
      mode: 'diff';
      path: string;
      lines: AgentEditDiffLine[];
      truncated: boolean;
      totalLines: number;
    };

function truncateMarkdownPreview(text: string, maxChars: number): { text: string; truncated: boolean } {
  const normalized = text.replace(/\s+$/g, '\n');
  if (normalized.length <= maxChars) {
    return { text: normalized, truncated: false };
  }
  const slice = normalized.slice(0, maxChars);
  const cut = Math.max(slice.lastIndexOf('\n\n'), slice.lastIndexOf('\n'));
  const body = (cut > maxChars / 3 ? slice.slice(0, cut) : slice).trimEnd();
  return { text: `${body}\n\n…`, truncated: true };
}

export function buildAgentEditBlockView(input: {
  path: string;
  diff: string;
  diffLineTone: (line: string) => AgentEditDiffLine['tone'];
}): AgentEditBlockView {
  const path = normalizeEditedFilePath(input.path);
  const diff = String(input.diff || '').replace(/\r\n/g, '\n').trimEnd();
  const allLines = diff ? diff.split('\n') : [];

  if (isMarkdownAgentEditPath(path) || languageForFilePath(path) === 'markdown') {
    const proposed = extractProposedFileContentFromDiff(diff);
    const totalLines = proposed ? proposed.split('\n').length : 0;
    if (proposed.trim()) {
      const preview = truncateMarkdownPreview(proposed, MAX_MARKDOWN_PREVIEW_CHARS);
      return {
        mode: 'markdown',
        path,
        previewMarkdown: preview.text,
        truncated: preview.truncated,
        totalLines,
      };
    }
  }

  const truncated = allLines.length > MAX_DIFF_PREVIEW_LINES;
  const visible = truncated ? allLines.slice(0, MAX_DIFF_PREVIEW_LINES) : allLines;
  return {
    mode: 'diff',
    path,
    lines: visible.map((text) => ({ text, tone: input.diffLineTone(text) })),
    truncated,
    totalLines: allLines.length,
  };
}

import type { IdeAgentEditSummary } from './ide-agent-center-view';
import { normalizeEditedFilePath } from './agent-transcript-blocks';
import { languageForFilePath } from './workspace-file-language';

export function agentEditReviewDocumentId(path: string): string {
  const normalized = normalizeEditedFilePath(path)
    .replace(/[^a-zA-Z0-9._-]+/g, '-')
    .replace(/^-+|-+$/g, '');
  return `draft:agent-edit-review:${normalized || 'file'}`;
}

export function isAgentEditReviewDocumentId(id: string | null | undefined): boolean {
  return Boolean(id?.startsWith('draft:agent-edit-review:'));
}

export function isMarkdownAgentEditPath(path: string): boolean {
  return languageForFilePath(normalizeEditedFilePath(path)) === 'markdown';
}

/**
 * Recover the proposed file body from a unified / agent edit diff.
 * Used so markdown reviews can render as real Markdown instead of green `+` lines.
 */
export function extractProposedFileContentFromDiff(diff: string): string {
  const lines = String(diff || '').replace(/\r\n/g, '\n').split('\n');
  const proposed: string[] = [];
  let sawContent = false;

  for (const line of lines) {
    if (
      line.startsWith('+++') ||
      line.startsWith('---') ||
      line.startsWith('@@') ||
      line.startsWith('diff --git') ||
      line.startsWith('index ')
    ) {
      continue;
    }
    if (line.startsWith('+')) {
      proposed.push(line.slice(1));
      sawContent = true;
      continue;
    }
    if (line.startsWith('-')) {
      // Deletions are not part of the proposed file body.
      continue;
    }
    // Context / bare lines (some agent edit blocks omit the leading space).
    if (line.startsWith(' ')) {
      proposed.push(line.slice(1));
      sawContent = true;
      continue;
    }
    if (line.length > 0 || sawContent) {
      proposed.push(line);
      if (line.length > 0) {
        sawContent = true;
      }
    }
  }

  return proposed.join('\n').replace(/^\n+/, '').replace(/\n+$/, '\n');
}

export function formatAgentEditReviewContent(
  edit: Pick<IdeAgentEditSummary, 'path' | 'diff' | 'added' | 'removed' | 'open'>,
): string {
  const path = normalizeEditedFilePath(edit.path);
  const diff = edit.diff.trim();

  // Markdown reviews store the proposed file body so Preview/Raw work like normal .md tabs.
  if (isMarkdownAgentEditPath(path)) {
    if (diff) {
      const proposed = extractProposedFileContentFromDiff(diff);
      if (proposed.trim()) {
        return proposed.endsWith('\n') ? proposed : `${proposed}\n`;
      }
    }
    if (edit.open) {
      return `# ${path}\n\n_Agent is still streaming changes for this file._\n`;
    }
    return `# ${path}\n\n_(No markdown content captured yet.)_\n`;
  }

  const header = [
    `# Agent review · ${path}`,
    `# +${edit.added}  -${edit.removed}`,
    '',
  ];

  if (edit.open) {
    header.push('Agent is still streaming changes for this file.', '');
  }

  if (diff) {
    return [...header, diff, ''].join('\n');
  }

  return [...header, '(No diff captured yet.)', ''].join('\n');
}

export function agentEditReviewDocumentTitle(path: string): string {
  const normalized = normalizeEditedFilePath(path);
  const base = normalized.split('/').pop() || normalized;
  return `${base} · review`;
}

/**
 * Prefer the real workspace file when:
 * - there is no diff yet (legacy), or
 * - this is a completed markdown edit (file is already saved; show Preview, not green + lines).
 */
export function shouldOpenWorkspaceFileForEditReview(
  edit: Pick<IdeAgentEditSummary, 'path' | 'diff' | 'open'>,
): boolean {
  if (edit.open) {
    return false;
  }
  if (!edit.diff.trim()) {
    return true;
  }
  // Completed markdown writes are already on disk — open the real file for Preview.
  return isMarkdownAgentEditPath(edit.path);
}

const DOCK_MARKDOWN_PREVIEW_CHARS = 1200;
const DOCK_DIFF_PREVIEW_LINES = 40;

/** Truncate proposed markdown for the agent-dock edit card (full file opens in editor). */
export function truncateMarkdownForDockPreview(
  markdown: string,
  maxChars = DOCK_MARKDOWN_PREVIEW_CHARS,
): { preview: string; truncated: boolean } {
  const trimmed = String(markdown || '').trim();
  if (!trimmed) {
    return { preview: '', truncated: false };
  }
  if (trimmed.length <= maxChars) {
    return { preview: trimmed, truncated: false };
  }
  const slice = trimmed.slice(0, maxChars);
  const cut = Math.max(slice.lastIndexOf('\n\n'), slice.lastIndexOf('\n'));
  const preview = (cut > maxChars / 3 ? slice.slice(0, cut) : slice).trimEnd();
  return { preview: `${preview}\n\n…`, truncated: true };
}

/** Limit raw unified-diff lines shown in the dock (non-markdown edits). */
export function truncateDiffLinesForDock(
  diff: string,
  maxLines = DOCK_DIFF_PREVIEW_LINES,
): { lines: string[]; truncated: boolean } {
  const lines = String(diff || '').replace(/\r\n/g, '\n').split('\n');
  if (lines.length <= maxLines) {
    return { lines, truncated: false };
  }
  return {
    lines: [...lines.slice(0, maxLines), `… ${lines.length - maxLines} more lines`],
    truncated: true,
  };
}

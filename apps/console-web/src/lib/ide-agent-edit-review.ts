import type { IdeAgentEditSummary } from './ide-agent-center-view';
import { normalizeEditedFilePath } from './agent-transcript-blocks';

export function agentEditReviewDocumentId(path: string): string {
  const normalized = normalizeEditedFilePath(path)
    .replace(/[^a-zA-Z0-9._-]+/g, '-')
    .replace(/^-+|-+$/g, '');
  return `draft:agent-edit-review:${normalized || 'file'}`;
}

export function formatAgentEditReviewContent(
  edit: Pick<IdeAgentEditSummary, 'path' | 'diff' | 'added' | 'removed' | 'open'>,
): string {
  const path = normalizeEditedFilePath(edit.path);
  const header = [
    `# Agent review · ${path}`,
    `# +${edit.added}  -${edit.removed}`,
    '',
  ];

  if (edit.open) {
    header.push('Agent is still streaming changes for this file.', '');
  }

  const diff = edit.diff.trim();
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

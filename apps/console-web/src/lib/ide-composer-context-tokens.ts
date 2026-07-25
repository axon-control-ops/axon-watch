import { sanitizeScrollbackText, scrollbackStorageKey } from './terminal-scrollback';

export const SELECTION_CONTEXT_TOKEN = '@selection';
export const TERMINAL_CONTEXT_TOKEN = '@terminal';

export const MAX_SELECTION_CONTEXT_CHARS = 4000;
export const MAX_TERMINAL_CONTEXT_CHARS = 4000;

export interface EditorSelectionContextPayload {
  file_path: string;
  start_line: number;
  end_line: number;
  text: string;
}

export function composerDraftIncludesToken(draft: string, token: string): boolean {
  const escaped = token.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  return new RegExp(`(^|\\s)${escaped}(?=\\s|$)`, 'm').test(draft);
}

export function truncateContextSnippet(text: string, maxChars: number): string {
  const trimmed = text.trim();
  if (trimmed.length <= maxChars) {
    return trimmed;
  }
  return `${trimmed.slice(0, maxChars - 1).trimEnd()}…`;
}

export function readStoredTerminalSnippet(
  workspaceId: string,
  sessionId = 'terminal-operator',
): string {
  if (typeof sessionStorage === 'undefined' || !workspaceId.trim()) {
    return '';
  }

  const raw = sessionStorage.getItem(scrollbackStorageKey(workspaceId, sessionId)) ?? '';
  return truncateContextSnippet(
    sanitizeScrollbackText(raw),
    MAX_TERMINAL_CONTEXT_CHARS,
  );
}

export function resolveComposerContextPayload(input: {
  draft: string;
  workspaceId: string | null;
  activeFilePath: string | null;
  terminalSessionId?: string | null;
  editorSelection: {
    startLine: number;
    endLine: number;
    text: string;
  } | null;
}): {
  editor_selection: EditorSelectionContextPayload | null;
  terminal_snippet: string | null;
} {
  const includeSelection = composerDraftIncludesToken(input.draft, SELECTION_CONTEXT_TOKEN);
  const includeTerminal = composerDraftIncludesToken(input.draft, TERMINAL_CONTEXT_TOKEN);

  const selectionText = input.editorSelection?.text.trim() ?? '';
  const editor_selection =
    includeSelection && input.activeFilePath && selectionText
      ? {
          file_path: input.activeFilePath,
          start_line: input.editorSelection?.startLine ?? 1,
          end_line: input.editorSelection?.endLine ?? 1,
          text: truncateContextSnippet(selectionText, MAX_SELECTION_CONTEXT_CHARS),
        }
      : null;

  const terminal_snippet =
    includeTerminal && input.workspaceId
      ? readStoredTerminalSnippet(
          input.workspaceId,
          input.terminalSessionId ?? 'terminal-operator',
        ) || null
      : null;

  return { editor_selection, terminal_snippet };
}

import {
  isBinaryFilePath,
  isImageFilePath,
  isPdfFilePath,
} from './workspace-file-language';
import {
  isSafeWorkspaceFilePath,
  normalizeWorkspaceFilePath,
} from './workspace-file-session';

function isInlinePreviewOnlyPath(path: string): boolean {
  return isPdfFilePath(path) || isImageFilePath(path);
}

/** Prefer a readable editor tab over PDF/image previews on workspace entry. */
export function pickPreferredActiveEditorPath(openedPaths: readonly string[]): string | null {
  const opened = uniquePaths(openedPaths);
  if (opened.length === 0) {
    return null;
  }

  const readme = opened.find((path) => path === 'README.md' || path.endsWith('/README.md'));
  if (readme) {
    return readme;
  }

  const markdown = opened.find(
    (path) => path.endsWith('.md') && !isInlinePreviewOnlyPath(path),
  );
  if (markdown) {
    return markdown;
  }

  const editable = opened.find((path) => !isBinaryFilePath(path));
  return editable ?? opened[0] ?? null;
}

export const OPEN_EDITOR_FILE_TABS_KEY = 'axon-x-open-editor-file-tabs-v1';
export const ACTIVE_EDITOR_DOCUMENT_IDS_KEY = 'axon-x-active-editor-document-v1';

function uniquePaths(values: readonly string[]): string[] {
  const seen = new Set<string>();
  const output: string[] = [];
  for (const value of values) {
    const next = normalizeWorkspaceFilePath(String(value ?? ''));
    if (!next || !isSafeWorkspaceFilePath(next) || seen.has(next)) {
      continue;
    }
    seen.add(next);
    output.push(next);
  }
  return output;
}

export function readOpenEditorFilePathsByWorkspace(): Record<string, string[]> {
  if (typeof window === 'undefined') {
    return {};
  }

  try {
    const raw = window.localStorage.getItem(OPEN_EDITOR_FILE_TABS_KEY);
    if (!raw) {
      return {};
    }
    const parsed = JSON.parse(raw) as unknown;
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
      return {};
    }

    const output: Record<string, string[]> = {};
    for (const [workspaceId, paths] of Object.entries(parsed)) {
      if (!workspaceId.trim() || !Array.isArray(paths)) {
        continue;
      }
      output[workspaceId] = uniquePaths(paths.map((value) => String(value ?? '')));
    }
    return output;
  } catch {
    return {};
  }
}

export function writeOpenEditorFilePathsForWorkspace(
  workspaceId: string,
  paths: readonly string[],
): void {
  if (typeof window === 'undefined') {
    return;
  }

  const id = workspaceId.trim();
  if (!id) {
    return;
  }

  const current = readOpenEditorFilePathsByWorkspace();
  const next = {
    ...current,
    [id]: uniquePaths(paths),
  };

  try {
    window.localStorage.setItem(OPEN_EDITOR_FILE_TABS_KEY, JSON.stringify(next));
  } catch {
    // Ignore quota failures.
  }
}

export function readActiveEditorDocumentIdsByWorkspace(): Record<string, string> {
  if (typeof window === 'undefined') {
    return {};
  }

  try {
    const raw = window.localStorage.getItem(ACTIVE_EDITOR_DOCUMENT_IDS_KEY);
    if (!raw) {
      return {};
    }
    const parsed = JSON.parse(raw) as unknown;
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
      return {};
    }

    const output: Record<string, string> = {};
    for (const [workspaceId, documentId] of Object.entries(parsed)) {
      const nextWorkspaceId = workspaceId.trim();
      const nextDocumentId = String(documentId ?? '').trim();
      if (!nextWorkspaceId || !nextDocumentId) {
        continue;
      }
      output[nextWorkspaceId] = nextDocumentId;
    }
    return output;
  } catch {
    return {};
  }
}

export function writeActiveEditorDocumentIdForWorkspace(
  workspaceId: string,
  documentId: string,
): void {
  if (typeof window === 'undefined') {
    return;
  }

  const nextWorkspaceId = workspaceId.trim();
  const nextDocumentId = documentId.trim();
  if (!nextWorkspaceId || !nextDocumentId) {
    return;
  }

  const current = readActiveEditorDocumentIdsByWorkspace();
  try {
    window.localStorage.setItem(
      ACTIVE_EDITOR_DOCUMENT_IDS_KEY,
      JSON.stringify({
        ...current,
        [nextWorkspaceId]: nextDocumentId,
      }),
    );
  } catch {
    // Ignore quota failures.
  }
}

/** Keep only paths that still exist in the workspace file listing. */
export function restoreOpenEditorFilePaths(
  storedPaths: readonly string[],
  availablePaths: readonly string[],
  fallbackPath: string | null,
): string[] {
  const available = new Set(availablePaths);
  const restored = uniquePaths(storedPaths).filter((path) => available.has(path));
  if (restored.length > 0) {
    return restored;
  }
  if (fallbackPath && available.has(fallbackPath)) {
    return [fallbackPath];
  }
  return fallbackPath ? [fallbackPath] : [];
}

export function resolveRestoredActiveEditorDocumentId(input: {
  storedDocumentId: string | null | undefined;
  openedPaths: readonly string[];
}): string | null {
  const opened = uniquePaths(input.openedPaths);
  if (opened.length === 0) {
    return null;
  }

  const preferredPath = pickPreferredActiveEditorPath(opened);
  if (!preferredPath) {
    return null;
  }

  const stored = String(input.storedDocumentId ?? '').trim();
  if (stored.startsWith('file:')) {
    const path = stored.slice('file:'.length);
    if (opened.includes(path)) {
      if (isInlinePreviewOnlyPath(path)) {
        return `file:${preferredPath}`;
      }
      return stored;
    }
  }

  return `file:${preferredPath}`;
}

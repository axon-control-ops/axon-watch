import type { EditorDocumentLanguage, WorkspaceDocumentDescriptor } from './workspace-documents';
import { isImageFilePath, languageForFilePath, workspaceFileDocumentId } from './workspace-file-language';

export type FileContentLoadState = 'idle' | 'loading' | 'loaded' | 'error';

export function normalizeWorkspaceFilePath(path: string): string {
  return path.trim().replace(/^\/+/, '').replace(/\/{2,}/g, '/');
}

export function isSafeWorkspaceFilePath(path: string): boolean {
  if (!path) {
    return false;
  }
  return !path.split('/').includes('..');
}

export function pickPreferredWorkspaceFilePath(
  entries: Array<{ path: string }>,
): string | null {
  return entries.find((entry) => entry.path === 'README.md')?.path ?? entries[0]?.path ?? null;
}

export function remapWorkspaceFileRecord<T>(
  record: Record<string, T>,
  oldPath: string,
  newPath: string,
): Record<string, T> {
  if (!(oldPath in record)) {
    return record;
  }

  const next = { ...record };
  next[newPath] = next[oldPath] as T;
  delete next[oldPath];
  return next;
}

export function remapWorkspaceFilePaths(
  paths: string[],
  oldPath: string,
  newPath: string,
): string[] {
  return paths.map((path) => (path === oldPath ? newPath : path));
}

export function buildOpenedFileDocuments(
  entries: Array<{ path: string; size_bytes: number }>,
  openedPaths: string[],
  contents: Record<string, string>,
  savedContents: Record<string, string>,
  loadStates: Record<string, FileContentLoadState>,
): WorkspaceDocumentDescriptor[] {
  const entryByPath = new Map(entries.map((entry) => [entry.path, entry]));

  return openedPaths.flatMap((path) => {
    const entry = entryByPath.get(path);
    if (!entry) {
      return [];
    }

    const content = contents[path] ?? '';
    const saved = savedContents[path];
    const loadState = loadStates[path] ?? 'idle';
    const pending = !isImageFilePath(path) && (loadState === 'idle' || loadState === 'loading');
    const imageFile = isImageFilePath(path);

    return [
      {
        id: workspaceFileDocumentId(path),
        title: path,
        language: languageForFilePath(path) as EditorDocumentLanguage,
        value: pending ? '' : content,
        description: imageFile
          ? `Image preview (${entry.size_bytes} bytes).`
          : pending
            ? 'Loading workspace file…'
            : `Workspace file on disk (${entry.size_bytes} bytes). Editable — use Save.`,
        source: 'file',
        filePath: path,
        readOnly: pending || imageFile,
        dirty: !imageFile && saved !== undefined && saved !== content,
      },
    ];
  });
}

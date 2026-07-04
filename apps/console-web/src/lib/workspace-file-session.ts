import type { EditorDocumentLanguage, WorkspaceDocumentDescriptor } from './workspace-documents';
import { languageForFilePath, workspaceFileDocumentId } from './workspace-file-language';

export type FileContentLoadState = 'idle' | 'loading' | 'loaded' | 'error';

export function pickPreferredWorkspaceFilePath(
  entries: Array<{ path: string }>,
): string | null {
  return entries.find((entry) => entry.path === 'README.md')?.path ?? entries[0]?.path ?? null;
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
    const pending = loadState === 'idle' || loadState === 'loading';

    return [
      {
        id: workspaceFileDocumentId(path),
        title: path,
        language: languageForFilePath(path) as EditorDocumentLanguage,
        value: pending ? '' : content,
        description: pending
          ? 'Loading workspace file…'
          : `Workspace file on disk (${entry.size_bytes} bytes). Editable — use Save.`,
        source: 'file',
        filePath: path,
        readOnly: pending,
        dirty: saved !== undefined && saved !== content,
      },
    ];
  });
}

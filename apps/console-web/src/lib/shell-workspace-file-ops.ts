import type { Ref } from 'vue';

import { renameWorkspaceFile, saveWorkspaceFile } from '../api/control-plane';
import { workspaceFileDocumentId } from './workspace-file-language';
import {
  isSafeWorkspaceFilePath,
  normalizeWorkspaceFilePath,
  remapWorkspaceFilePaths,
  remapWorkspaceFileRecord,
  type FileContentLoadState,
} from './workspace-file-session';

interface WorkspaceFileEntry {
  path: string;
  size_bytes: number;
}

interface WorkspaceFileOpsInput {
  currentWorkspace: Ref<{ workspace_id: string } | null | undefined>;
  workspaceFilesError: Ref<string | null>;
  workspaceFileEntries: Ref<WorkspaceFileEntry[]>;
  fileSaveState: Ref<string>;
  fileSaveError: Ref<string | null>;
  fileContents: Ref<Record<string, string>>;
  fileSavedContents: Ref<Record<string, string>>;
  fileContentLoadStates: Ref<Record<string, FileContentLoadState>>;
  activeWorkspaceFilePath: Ref<string | null>;
  activeEditorDocumentId: Ref<string | null>;
  openedFilePaths: Ref<string[]>;
  openWorkspaceFile: (path: string) => Promise<void>;
  loadWorkspaceFiles: () => Promise<void>;
  ensureWorkspaceFileLoaded: (path: string) => Promise<void>;
}

function promptWorkspaceFilePath(message: string, defaultValue = ''): string | null {
  if (typeof window === 'undefined') {
    return defaultValue || null;
  }
  const response = window.prompt(message, defaultValue)?.trim() ?? '';
  if (!response) {
    return null;
  }
  const normalized = normalizeWorkspaceFilePath(response);
  if (!isSafeWorkspaceFilePath(normalized)) {
    return null;
  }
  return normalized;
}

function sortWorkspaceFileEntries(entries: WorkspaceFileEntry[]): WorkspaceFileEntry[] {
  return entries.sort((left, right) => left.path.localeCompare(right.path));
}

export function createWorkspaceFileOps(input: WorkspaceFileOpsInput) {
  async function createWorkspaceFile(requestedPath?: string | null): Promise<void> {
    const workspaceId = input.currentWorkspace.value?.workspace_id;
    if (!workspaceId) {
      input.workspaceFilesError.value = 'Select a workspace before creating a file.';
      return;
    }

    input.workspaceFilesError.value = null;
    const path = requestedPath
      ? normalizeWorkspaceFilePath(requestedPath)
      : promptWorkspaceFilePath('New workspace file path', 'src/new-file.txt');
    if (!path || !isSafeWorkspaceFilePath(path)) {
      if (requestedPath) {
        input.workspaceFilesError.value = 'Enter a safe relative path inside the workspace.';
      }
      return;
    }

    if (input.workspaceFileEntries.value.some((entry) => entry.path === path)) {
      await input.openWorkspaceFile(path);
      return;
    }

    input.fileSaveState.value = 'saving';
    input.fileSaveError.value = null;
    try {
      const payload = await saveWorkspaceFile(workspaceId, path, '');
      input.workspaceFileEntries.value = sortWorkspaceFileEntries([
        ...input.workspaceFileEntries.value,
        payload,
      ]);
      input.fileContents.value = {
        ...input.fileContents.value,
        [path]: '',
      };
      input.fileSavedContents.value = {
        ...input.fileSavedContents.value,
        [path]: '',
      };
      input.fileContentLoadStates.value = {
        ...input.fileContentLoadStates.value,
        [path]: 'loaded',
      };
      await input.openWorkspaceFile(path);
    } catch (error) {
      input.fileSaveError.value =
        error instanceof Error ? error.message : 'workspace file create failed';
    } finally {
      input.fileSaveState.value = 'idle';
    }
  }

  async function createWorkspaceFolder(requestedPath?: string | null): Promise<void> {
    const workspaceId = input.currentWorkspace.value?.workspace_id;
    if (!workspaceId) {
      input.workspaceFilesError.value = 'Select a workspace before creating a folder.';
      return;
    }

    input.workspaceFilesError.value = null;
    const folderPath = requestedPath
      ? normalizeWorkspaceFilePath(requestedPath)
      : promptWorkspaceFilePath('New folder path', 'src/new-folder');
    if (!folderPath || !isSafeWorkspaceFilePath(folderPath)) {
      if (requestedPath) {
        input.workspaceFilesError.value = 'Enter a safe relative path inside the workspace.';
      }
      return;
    }

    const markerPath = `${folderPath.replace(/\/+$/, '')}/.gitkeep`;
    if (input.workspaceFileEntries.value.some((entry) => entry.path === markerPath)) {
      return;
    }

    input.fileSaveState.value = 'saving';
    input.fileSaveError.value = null;
    try {
      const payload = await saveWorkspaceFile(workspaceId, markerPath, '');
      input.workspaceFileEntries.value = sortWorkspaceFileEntries([
        ...input.workspaceFileEntries.value,
        payload,
      ]);
      await input.loadWorkspaceFiles();
    } catch (error) {
      input.fileSaveError.value =
        error instanceof Error ? error.message : 'workspace folder create failed';
    } finally {
      input.fileSaveState.value = 'idle';
    }
  }

  async function renameActiveWorkspaceFile(): Promise<void> {
    const workspaceId = input.currentWorkspace.value?.workspace_id;
    const oldPath = input.activeWorkspaceFilePath.value;
    if (!workspaceId || !oldPath) {
      input.workspaceFilesError.value = 'Open a workspace file before renaming it.';
      return;
    }

    input.workspaceFilesError.value = null;
    const newPath = promptWorkspaceFilePath('Rename workspace file to', oldPath);
    if (!newPath || newPath === oldPath) {
      return;
    }

    input.fileSaveState.value = 'saving';
    input.fileSaveError.value = null;
    try {
      const payload = await renameWorkspaceFile(workspaceId, oldPath, newPath);
      input.workspaceFileEntries.value = sortWorkspaceFileEntries(
        input.workspaceFileEntries.value.map((entry) =>
          entry.path === oldPath ? { path: payload.path, size_bytes: payload.size_bytes } : entry,
        ),
      );
      input.fileContents.value = remapWorkspaceFileRecord(input.fileContents.value, oldPath, newPath);
      input.fileSavedContents.value = remapWorkspaceFileRecord(
        input.fileSavedContents.value,
        oldPath,
        newPath,
      );
      input.fileContentLoadStates.value = remapWorkspaceFileRecord(
        input.fileContentLoadStates.value,
        oldPath,
        newPath,
      );
      input.openedFilePaths.value = remapWorkspaceFilePaths(
        input.openedFilePaths.value,
        oldPath,
        newPath,
      );
      input.activeEditorDocumentId.value = workspaceFileDocumentId(newPath);
      await input.ensureWorkspaceFileLoaded(newPath);
    } catch (error) {
      input.fileSaveError.value =
        error instanceof Error ? error.message : 'workspace file rename failed';
    } finally {
      input.fileSaveState.value = 'idle';
    }
  }

  return {
    createWorkspaceFile,
    createWorkspaceFolder,
    renameActiveWorkspaceFile,
  };
}

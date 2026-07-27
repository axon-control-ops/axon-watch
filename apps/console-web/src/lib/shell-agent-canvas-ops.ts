import type { Ref } from 'vue';

import type { IdeAgentEditSummary } from './ide-agent-center-view';
import {
  agentEditReviewDocumentId,
  agentEditReviewDocumentTitle,
  formatAgentEditReviewContent,
  shouldOpenWorkspaceFileForEditReview,
} from './ide-agent-edit-review';
import { resolveAgentEditOpenPath } from './agent-edit-open-path';
import {
  buildImageCanvasDocument,
  upsertImageCanvasDocument,
} from './image-canvas-open';
import { persistEditorMarkdownPreviewEnabled } from './editor-markdown-preview-prefs';
import { languageForFilePath, workspaceFileDocumentId } from './workspace-file-language';
import type { EditorDocumentLanguage, WorkspaceDocumentDescriptor } from './workspace-documents';

type LayoutMode = 'operator' | 'ide';

export function createShellAgentCanvasOps(input: {
  layoutMode: Ref<LayoutMode>;
  setLayoutMode: (mode: LayoutMode) => void;
  currentWorkspace: Ref<{ workspace_id: string; project_root?: string | null } | null | undefined>;
  draftDocuments: Ref<WorkspaceDocumentDescriptor[]>;
  openedFilePaths: Ref<string[]>;
  activeEditorDocumentId: Ref<string | null>;
  openWorkspaceFile: (path: string) => Promise<void>;
  ensureWorkspaceFileLoaded: (path: string) => Promise<void>;
}) {
  function ensureIdeLayout(): void {
    if (input.layoutMode.value !== 'ide') {
      input.setLayoutMode('ide');
    }
  }

  function openImageInCanvas(options: {
    path: string;
    attachmentUrl?: string | null;
  }): void {
    ensureIdeLayout();
    const workspace = input.currentWorkspace.value;
    const doc = buildImageCanvasDocument({
      path: options.path,
      attachmentUrl: options.attachmentUrl,
      workspaceId: workspace?.workspace_id,
      projectRoot: workspace?.project_root,
    });
    if (doc) {
      input.draftDocuments.value = upsertImageCanvasDocument(input.draftDocuments.value, doc);
      input.activeEditorDocumentId.value = doc.id;
      return;
    }
    const path = resolveAgentEditOpenPath(options.path, workspace?.project_root);
    if (path) {
      void input.openWorkspaceFile(path);
    }
  }

  function openAgentEditReview(
    edit: Pick<IdeAgentEditSummary, 'path' | 'diff' | 'added' | 'removed' | 'open'>,
  ): void {
    const path = resolveAgentEditOpenPath(
      edit.path,
      input.currentWorkspace.value?.project_root,
    );
    if (!path) {
      return;
    }
    ensureIdeLayout();
    if (shouldOpenWorkspaceFileForEditReview(edit)) {
      if (languageForFilePath(path) === 'markdown') {
        persistEditorMarkdownPreviewEnabled(workspaceFileDocumentId(path), true);
      }
      void input.openWorkspaceFile(path);
      return;
    }

    if (!input.openedFilePaths.value.includes(path)) {
      input.openedFilePaths.value = [...input.openedFilePaths.value, path];
      void input.ensureWorkspaceFileLoaded(path);
    }

    const id = agentEditReviewDocumentId(path);
    const title = agentEditReviewDocumentTitle(path);
    const content = formatAgentEditReviewContent(edit);
    const language = (
      languageForFilePath(path) === 'markdown' ? 'markdown' : 'plaintext'
    ) as EditorDocumentLanguage;
    const existing = input.draftDocuments.value.find((document) => document.id === id);

    if (existing) {
      input.draftDocuments.value = input.draftDocuments.value.map((document) =>
        document.id === id
          ? {
              ...document,
              title,
              language,
              value: content,
              dirty: document.value !== content,
            }
          : document,
      );
    } else {
      input.draftDocuments.value = [
        ...input.draftDocuments.value,
        {
          id,
          title,
          language,
          value: content,
          description:
            language === 'markdown'
              ? 'Agent markdown review (Preview/Raw). Diff markers are stripped for readable rendering.'
              : 'Agent proposed changes from the transcript diff (read-only review).',
          source: 'draft',
          readOnly: true,
          dirty: false,
          filePath: path,
        },
      ];
    }

    if (language === 'markdown') {
      persistEditorMarkdownPreviewEnabled(id, true);
    }
    input.activeEditorDocumentId.value = id;
  }

  return { openImageInCanvas, openAgentEditReview };
}

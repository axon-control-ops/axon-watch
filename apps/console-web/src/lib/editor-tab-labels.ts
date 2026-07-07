import type { WorkspaceDocumentDescriptor } from './workspace-documents';

export type EditorTabLabelInput = {
  id: string;
  resourcePath: string;
};

const TAB_LABEL_MAX = 28;

function pathSegments(path: string): string[] {
  return path
    .replace(/\\/g, '/')
    .split('/')
    .map((segment) => segment.trim())
    .filter(Boolean);
}

function basename(path: string): string {
  const segments = pathSegments(path);
  return segments[segments.length - 1] ?? path;
}

function truncateTabLabel(label: string): string {
  const trimmed = label.trim();
  if (trimmed.length <= TAB_LABEL_MAX) {
    return trimmed;
  }
  return `${trimmed.slice(0, TAB_LABEL_MAX - 1).trimEnd()}…`;
}

/** Workspace-relative path for tab disambiguation (Cursor/VS Code-style). */
export function editorDocumentResourcePath(document: WorkspaceDocumentDescriptor): string {
  if (document.source === 'file' && document.filePath) {
    return document.filePath.replace(/\\/g, '/');
  }

  if (document.source === 'draft') {
    return `agent-reports/${document.id.replace(/^draft:/, '')}.md`;
  }

  return document.title.replace(/\\/g, '/');
}

/** Cursor/VS Code-style tab labels for workspace files. */
export function buildEditorTabLabels(inputs: EditorTabLabelInput[]): Map<string, string> {
  const labels = new Map<string, string>();

  for (const input of inputs) {
    const segments = pathSegments(input.resourcePath);
    const fileName = basename(input.resourcePath);
    const peers = inputs.filter((candidate) => candidate.id !== input.id);
    const peerBasenames = peers.map((candidate) => basename(candidate.resourcePath));

    if (!peerBasenames.includes(fileName)) {
      labels.set(input.id, fileName);
      continue;
    }

    let chosen = input.resourcePath;
    for (let depth = 2; depth <= segments.length; depth += 1) {
      const candidate = segments.slice(-depth).join('/');
      const collisions = peers.filter((peer) => {
        const peerSegments = pathSegments(peer.resourcePath);
        const peerCandidate = peerSegments.slice(-depth).join('/');
        return peerCandidate === candidate;
      });
      if (collisions.length === 0) {
        chosen = candidate;
        break;
      }
    }

    labels.set(input.id, chosen);
  }

  return labels;
}

export function editorTabLabelsForDocuments(
  documents: WorkspaceDocumentDescriptor[],
): Map<string, string> {
  const fileLike = documents.filter((document) => document.source !== 'draft');
  const fileLabels = buildEditorTabLabels(
    fileLike.map((document) => ({
      id: document.id,
      resourcePath: editorDocumentResourcePath(document),
    })),
  );

  const labels = new Map<string, string>(fileLabels);
  const draftTitles = documents
    .filter((document) => document.source === 'draft')
    .map((document) => truncateTabLabel(document.title.replace(/^Agent · /, '').trim() || 'Agent report'));

  for (const document of documents) {
    if (document.source !== 'draft') {
      continue;
    }
    const displayTitle = truncateTabLabel(
      document.title.replace(/^Agent · /, '').trim() || 'Agent report',
    );
    const duplicateTitle = draftTitles.filter((title) => title === displayTitle).length > 1;
    labels.set(
      document.id,
      duplicateTitle ? truncateTabLabel(document.title.trim()) : displayTitle,
    );
  }

  return labels;
}

export function formatAgentDraftTitle(title: string): string {
  const trimmed = title.trim() || 'Agent report';
  return trimmed.startsWith('Agent · ') ? trimmed : `Agent · ${trimmed}`;
}

export function editorTabLabelForDocument(
  document: WorkspaceDocumentDescriptor,
  labels: Map<string, string>,
): string {
  return labels.get(document.id) ?? truncateTabLabel(document.title);
}

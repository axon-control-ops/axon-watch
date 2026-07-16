import type { WorkspaceDocumentDescriptor } from './workspace-documents';

export function upsertAgentDraftDocument(input: {
  drafts: WorkspaceDocumentDescriptor[];
  title: string;
  content: string;
  readOnly: boolean;
  planId?: string;
  idFactory: (slug: string) => string;
}): { drafts: WorkspaceDocumentDescriptor[]; id: string } {
  const normalizedTitle = input.title.toLowerCase();
  const existing = input.drafts.find(
    (document) => document.source === 'draft' && document.title.toLowerCase() === normalizedTitle,
  );
  if (existing) {
    return {
      id: existing.id,
      drafts: input.drafts.map((document) =>
        document.id === existing.id
          ? {
              ...document,
              value: input.content,
              dirty: document.value !== input.content,
              readOnly: input.readOnly || document.readOnly,
              planId: input.planId ?? document.planId,
            }
          : document,
      ),
    };
  }

  const slug = normalizedTitle.replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 48);
  const id = input.idFactory(slug || 'response');
  return {
    id,
    drafts: [
      ...input.drafts,
      {
        id,
        title: input.title,
        language: 'markdown',
        value: input.content,
        description: input.readOnly
          ? 'Saved Plan opened in the editor. Raw/Preview toggle is in the tab bar.'
          : 'Agent response opened in the editor. Raw/Preview toggle is in the tab bar.',
        source: 'draft',
        readOnly: input.readOnly,
        dirty: false,
        planId: input.planId,
      },
    ],
  };
}

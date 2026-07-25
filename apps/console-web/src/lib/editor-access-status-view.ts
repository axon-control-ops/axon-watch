export type EditorAccessStatusTone =
  | 'saved'
  | 'unsaved'
  | 'read-only'
  | 'loading'
  | 'preview'
  | 'empty';

export type EditorAccessReadOnlyReason =
  | 'loading'
  | 'binary'
  | 'image'
  | 'agent-review-diff'
  | 'agent-review-markdown'
  | 'plan'
  | 'dto'
  | 'generic';

export type EditorAccessStatus = {
  label: string;
  tone: EditorAccessStatusTone;
  title?: string;
  ariaLabel?: string;
  opensSourceControl: boolean;
};

const READ_ONLY_COPY: Record<
  EditorAccessReadOnlyReason,
  Pick<EditorAccessStatus, 'label' | 'tone' | 'title' | 'ariaLabel'>
> = {
  loading: {
    label: 'Loading',
    tone: 'loading',
    title: 'File content is loading — editing unlocks when the read finishes',
    ariaLabel: 'Loading file content. Editing unlocks when the read finishes.',
  },
  image: {
    label: 'Preview',
    tone: 'preview',
    title: 'Image preview — not editable as text',
    ariaLabel: 'Image preview. Not editable as text.',
  },
  binary: {
    label: 'Read-only',
    tone: 'read-only',
    title: 'Binary file — not editable as text',
    ariaLabel: 'Read-only binary file. Not editable as text.',
  },
  'agent-review-diff': {
    label: 'Review',
    tone: 'read-only',
    title: 'Agent diff review — accept or reject changes from the dock',
    ariaLabel: 'Agent diff review. Read-only until you accept or reject changes.',
  },
  'agent-review-markdown': {
    label: 'Review',
    tone: 'read-only',
    title: 'Agent markdown review — read-only until you accept or reject changes',
    ariaLabel: 'Agent markdown review. Read-only until you accept or reject changes.',
  },
  plan: {
    label: 'Read-only',
    tone: 'read-only',
    title: 'Plan viewer — use Build plan in the toolbar to run this plan',
    ariaLabel: 'Read-only plan viewer. Use Build plan in the toolbar to run this plan.',
  },
  dto: {
    label: 'Snapshot',
    tone: 'read-only',
    title: 'Runtime snapshot assembled from live workspace data',
    ariaLabel: 'Read-only runtime snapshot assembled from live workspace data.',
  },
  generic: {
    label: 'Read-only',
    tone: 'read-only',
  },
};

/** Infer why the active editor tab is read-only for status-bar copy. */
export function resolveEditorAccessReadOnlyReason(input: {
  readOnly: boolean;
  source?: 'dto' | 'file' | 'draft';
  planId?: string | null;
  description?: string;
  isAgentEditReview: boolean;
  isMarkdownEditorDocument: boolean;
  isBinaryEditorDocument: boolean;
  isImageEditorDocument: boolean;
}): EditorAccessReadOnlyReason | null {
  if (!input.readOnly) {
    return null;
  }

  const description = (input.description ?? '').trim();
  if (description.startsWith('Loading workspace file')) {
    return 'loading';
  }
  if (input.isImageEditorDocument) {
    return 'image';
  }
  if (input.isBinaryEditorDocument || description.includes('Binary file')) {
    return 'binary';
  }
  if (input.isAgentEditReview && input.isMarkdownEditorDocument) {
    return 'agent-review-markdown';
  }
  if (input.isAgentEditReview) {
    return 'agent-review-diff';
  }
  if (input.planId) {
    return 'plan';
  }
  if (input.source === 'dto') {
    return 'dto';
  }
  if (input.source === 'draft') {
    return input.isMarkdownEditorDocument ? 'agent-review-markdown' : 'agent-review-diff';
  }

  return 'generic';
}

/** Save-state label for the IDE editor status bar meta strip. */
export function buildEditorAccessStatus(input: {
  hasDocument: boolean;
  readOnly: boolean;
  dirty: boolean;
  readOnlyReason?: EditorAccessReadOnlyReason | null;
}): EditorAccessStatus {
  if (!input.hasDocument) {
    return {
      label: 'No document',
      tone: 'empty',
      opensSourceControl: false,
    };
  }

  if (input.readOnly) {
    const reason = input.readOnlyReason ?? 'generic';
    return {
      ...READ_ONLY_COPY[reason],
      opensSourceControl: false,
    };
  }

  if (input.dirty) {
    return {
      label: 'Unsaved',
      tone: 'unsaved',
      title: 'Unsaved changes — open Source Control (Ctrl/Cmd+Shift+G)',
      ariaLabel: 'Unsaved changes. Open Source Control sidebar.',
      opensSourceControl: true,
    };
  }

  return {
    label: 'Saved',
    tone: 'saved',
    opensSourceControl: false,
  };
}

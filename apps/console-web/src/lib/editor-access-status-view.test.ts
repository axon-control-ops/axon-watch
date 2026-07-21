import { describe, expect, it } from 'vitest';

import {
  buildEditorAccessStatus,
  resolveEditorAccessReadOnlyReason,
} from './editor-access-status-view';

describe('resolveEditorAccessReadOnlyReason', () => {
  it('returns null for editable tabs and maps common read-only cases', () => {
    expect(
      resolveEditorAccessReadOnlyReason({
        readOnly: false,
        isAgentEditReview: false,
        isMarkdownEditorDocument: false,
        isBinaryEditorDocument: false,
        isImageEditorDocument: false,
      }),
    ).toBeNull();

    expect(
      resolveEditorAccessReadOnlyReason({
        readOnly: true,
        description: 'Loading workspace file…',
        isAgentEditReview: false,
        isMarkdownEditorDocument: false,
        isBinaryEditorDocument: false,
        isImageEditorDocument: false,
      }),
    ).toBe('loading');

    expect(
      resolveEditorAccessReadOnlyReason({
        readOnly: true,
        isAgentEditReview: false,
        isMarkdownEditorDocument: false,
        isBinaryEditorDocument: false,
        isImageEditorDocument: true,
      }),
    ).toBe('image');

    expect(
      resolveEditorAccessReadOnlyReason({
        readOnly: true,
        isAgentEditReview: true,
        isMarkdownEditorDocument: false,
        isBinaryEditorDocument: false,
        isImageEditorDocument: false,
      }),
    ).toBe('agent-review-diff');

    expect(
      resolveEditorAccessReadOnlyReason({
        readOnly: true,
        source: 'dto',
        isAgentEditReview: false,
        isMarkdownEditorDocument: false,
        isBinaryEditorDocument: false,
        isImageEditorDocument: false,
      }),
    ).toBe('dto');
  });
});

describe('buildEditorAccessStatus', () => {
  it('describes empty, read-only, saved, and unsaved editor states', () => {
    expect(
      buildEditorAccessStatus({ hasDocument: false, readOnly: false, dirty: false }),
    ).toEqual({
      label: 'No document',
      tone: 'empty',
      opensSourceControl: false,
    });

    expect(
      buildEditorAccessStatus({
        hasDocument: true,
        readOnly: true,
        dirty: false,
        readOnlyReason: 'generic',
      }),
    ).toEqual({
      label: 'Read-only',
      tone: 'read-only',
      opensSourceControl: false,
    });

    expect(
      buildEditorAccessStatus({ hasDocument: true, readOnly: false, dirty: false }),
    ).toEqual({
      label: 'Saved',
      tone: 'saved',
      opensSourceControl: false,
    });
  });

  it('offers Source Control recovery when the active tab has unsaved edits', () => {
    const status = buildEditorAccessStatus({
      hasDocument: true,
      readOnly: false,
      dirty: true,
    });

    expect(status.label).toBe('Unsaved');
    expect(status.tone).toBe('unsaved');
    expect(status.opensSourceControl).toBe(true);
    expect(status.title).toContain('Source Control');
    expect(status.ariaLabel).toContain('Unsaved changes');
  });

  it('uses contextual read-only labels and tooltips', () => {
    expect(
      buildEditorAccessStatus({
        hasDocument: true,
        readOnly: true,
        dirty: false,
        readOnlyReason: 'loading',
      }),
    ).toMatchObject({
      label: 'Loading',
      tone: 'loading',
      title: expect.stringContaining('loading'),
    });

    expect(
      buildEditorAccessStatus({
        hasDocument: true,
        readOnly: true,
        dirty: false,
        readOnlyReason: 'agent-review-diff',
      }),
    ).toMatchObject({
      label: 'Review',
      title: expect.stringContaining('diff review'),
    });

    expect(
      buildEditorAccessStatus({
        hasDocument: true,
        readOnly: true,
        dirty: false,
        readOnlyReason: 'dto',
      }),
    ).toMatchObject({
      label: 'Snapshot',
      title: expect.stringContaining('snapshot'),
    });
  });
});

import { describe, expect, it } from 'vitest';

import {
  buildVaxonComposerSubmission,
  shouldSubmitVaxonComposer,
  vaxonComposerSubmissionIntent,
} from './vaxon-executive-composer';

describe('VAXON executive composer', () => {
  it('keeps Ask text unmodified and carries the safe ask intent', () => {
    expect(buildVaxonComposerSubmission('What is our highest risk?', 'ask')).toBe(
      'What is our highest risk?',
    );
    expect(vaxonComposerSubmissionIntent('ask')).toBe('ask');
  });

  it('envelopes a dispatch mission and marks it as an explicit dispatch', () => {
    expect(buildVaxonComposerSubmission('Restore the billing flow', 'dispatch')).toBe(
      'Mission:\nRestore the billing flow',
    );
    expect(vaxonComposerSubmissionIntent('dispatch')).toBe('dispatch');
  });

  it('uses Enter to send and Shift+Enter to add a mission detail line', () => {
    expect(shouldSubmitVaxonComposer({ key: 'Enter', shiftKey: false })).toBe(true);
    expect(shouldSubmitVaxonComposer({ key: 'Enter', shiftKey: true })).toBe(false);
    expect(
      shouldSubmitVaxonComposer({ key: 'Enter', shiftKey: false, isComposing: true }),
    ).toBe(false);
  });
});

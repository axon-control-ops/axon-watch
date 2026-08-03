import { describe, expect, it } from 'vitest';

import {
  buildVaxonComposerSubmission,
  inferVaxonComposerMode,
  shouldSubmitVaxonComposer,
} from './vaxon-executive-composer';

describe('vaxon executive composer', () => {
  it('turns mission mode intent into an explicit mission conversation artifact', () => {
    expect(buildVaxonComposerSubmission('Build the authentication flow', 'mission')).toBe(
      'Mission:\nBuild the authentication flow',
    );
    expect(
      buildVaxonComposerSubmission(
        'Mission Title: Authentication\nObjective: Build login',
        'mission',
      ),
    ).toBe('Mission Title: Authentication\nObjective: Build login');
  });

  it('keeps ask mode conversational', () => {
    expect(buildVaxonComposerSubmission('What is our highest risk?', 'ask')).toBe(
      'What is our highest risk?',
    );
  });

  it('infers conversational questions without asking the operator to choose a mode', () => {
    expect(inferVaxonComposerMode('')).toBe('mission');
    expect(inferVaxonComposerMode('What is our highest risk?')).toBe('ask');
    expect(inferVaxonComposerMode('Show the delivery status')).toBe('ask');
    expect(inferVaxonComposerMode('Repair the authentication flow')).toBe('mission');
  });

  it('submits on Enter and preserves Shift+Enter for mission detail', () => {
    expect(
      shouldSubmitVaxonComposer({ key: 'Enter', shiftKey: false }),
    ).toBe(true);
    expect(
      shouldSubmitVaxonComposer({ key: 'Enter', shiftKey: true }),
    ).toBe(false);
    expect(
      shouldSubmitVaxonComposer({
        key: 'Enter',
        shiftKey: false,
        isComposing: true,
      }),
    ).toBe(false);
  });
});

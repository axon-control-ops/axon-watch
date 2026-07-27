import { beforeEach, describe, expect, it } from 'vitest';

import {
  dismissVaxonBriefingInteraction,
  getVaxonBriefingInteraction,
  recordVaxonBriefingInteraction,
  resetVaxonBriefingInteractionForTests,
  vaxonBriefingInteractionKey,
} from './vaxon-briefing-interaction';

describe('vaxon briefing interaction persistence', () => {
  beforeEach(() => {
    resetVaxonBriefingInteractionForTests();
  });

  it('keeps the latest briefing until dismissed', () => {
    recordVaxonBriefingInteraction({
      workspaceId: 'workspace_dashpro',
      line: 'Shall I dig into the CI failure?',
      utteranceKey: vaxonBriefingInteractionKey('Shall I dig into the CI failure?'),
    });
    expect(getVaxonBriefingInteraction('workspace_dashpro')?.line).toContain('CI failure');
    dismissVaxonBriefingInteraction('workspace_dashpro');
    expect(getVaxonBriefingInteraction('workspace_dashpro')).toBeNull();
  });

  it('does not reopen a dismissed utterance key', () => {
    const key = vaxonBriefingInteractionKey('Heads up — signal open.');
    recordVaxonBriefingInteraction({
      workspaceId: 'workspace_dashpro',
      line: 'Heads up — signal open.',
      utteranceKey: key,
    });
    dismissVaxonBriefingInteraction('workspace_dashpro');
    recordVaxonBriefingInteraction({
      workspaceId: 'workspace_dashpro',
      line: 'Heads up — signal open.',
      utteranceKey: key,
    });
    expect(getVaxonBriefingInteraction('workspace_dashpro')).toBeNull();
  });
});

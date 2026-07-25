import { describe, expect, it } from 'vitest';

import {
  resolveSidebarSpeechChipView,
  sidebarSpeechCanExpand,
} from './sidebar-speech-chip-view';

describe('resolveSidebarSpeechChipView', () => {
  it('labels the speaking agent and shows spoken text', () => {
    const view = resolveSidebarSpeechChipView({
      spokenText: 'I will render the submission HTML to PDF next.',
      speaker: {
        kind: 'employee',
        id: 'emp_lila',
        name: 'Lila',
        roleLabel: 'Frontend',
      },
      speaking: true,
      fallbackPersonaName: 'VAXON',
    });
    expect(view.statusLabel).toBe('Lila · speaking');
    expect(view.displayText).toContain('render the submission HTML');
    expect(view.empty).toBe(false);
  });

  it('keeps the last spoken line after speech ends', () => {
    const live = resolveSidebarSpeechChipView({
      spokenText: 'Locked the graduation confirmation path.',
      speaker: {
        kind: 'employee',
        id: 'emp_lila',
        name: 'Lila',
        roleLabel: 'Frontend',
      },
      speaking: true,
      fallbackPersonaName: 'VAXON',
    });
    const after = resolveSidebarSpeechChipView({
      spokenText: null,
      speaker: null,
      speaking: false,
      fallbackPersonaName: 'VAXON',
      stickyText: live.stickyText,
      stickySpeakerName: live.stickySpeakerName,
    });
    expect(after.statusLabel).toBe('Lila · last spoken');
    expect(after.displayText).toContain('graduation confirmation');
  });

  it('offers expansion only for transcript copy that exceeds the compact card', () => {
    expect(sidebarSpeechCanExpand('Short spoken update.')).toBe(false);
    expect(sidebarSpeechCanExpand('Line 1\nLine 2\nLine 3\nLine 4\nLine 5')).toBe(true);
    expect(sidebarSpeechCanExpand('A'.repeat(181))).toBe(true);
  });
});

import { describe, expect, it } from 'vitest';

import {
  jarvisAgentStartLine,
  jarvisAlertSpeech,
  jarvisSpokenLine,
} from './kairo-voice-script';

describe('jarvisAgentStartLine', () => {
  it('opens full-access turns with assistant intent', () => {
    expect(jarvisAgentStartLine({ fullAccess: true, activeFile: 'README.md' })).toContain(
      'the README',
    );
    expect(jarvisAgentStartLine({ fullAccess: false, activeFile: null })).toMatch(/take a look/i);
  });
});

describe('jarvisSpokenLine', () => {
  const ctx = { fullAccess: true, activeFile: 'README.md' };

  it('never reads raw tool labels aloud', () => {
    expect(
      jarvisSpokenLine({ key: 'tool:0', message: 'Read README.md', toolLabel: 'Read README.md' }, ctx),
    ).toBe("I'm pulling up the README for you.");
    expect(jarvisSpokenLine({ key: 'tool:1', message: 'Grep workspace', toolLabel: 'Grep workspace' }, ctx)).toBeNull();
  });

  it('speaks edits and completion like an assistant', () => {
    expect(
      jarvisSpokenLine({ key: 'edit:0', message: 'README.md +1 -0', editPath: 'README.md' }, ctx),
    ).toMatch(/updated the README/i);
    expect(
      jarvisSpokenLine({ key: 'done', message: 'Done', editPath: 'README.md', editCount: 1 }, ctx),
    ).toMatch(/all set/i);
  });
});

describe('jarvisAlertSpeech', () => {
  it('rewrites briefing alerts into natural assistant speech', () => {
    expect(jarvisAlertSpeech('KAIRO: 1 approval waiting for your review.')).toMatch(/approval/i);
    expect(jarvisAlertSpeech('Standing by while briefing loads.')).toMatch(/standing by/i);
  });
});

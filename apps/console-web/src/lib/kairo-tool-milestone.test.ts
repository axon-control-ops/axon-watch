import { describe, expect, it } from 'vitest';

import { toolMilestoneSpeakLine } from './kairo-tool-milestone';

describe('kairo tool milestone', () => {
  it('skips ambient orientation docs like OPERATIONS.md', () => {
    expect(toolMilestoneSpeakLine('Read OPERATIONS.md')).toBe('');
    expect(toolMilestoneSpeakLine('Read docs/README.md')).toBe('');
    expect(toolMilestoneSpeakLine('Read AGENTS.md')).toBe('');
  });

  it('grounds real file reads in the operator prompt', () => {
    expect(
      toolMilestoneSpeakLine(
        'Read services/control-plane/app/research/availability.py',
        { operatorPrompt: 'run production OTA and monitor for errors' },
      ),
    ).toBe('Checking availability.py for: run production OTA and monitor for errors');
  });

  it('explains edit tools with task context', () => {
    expect(
      toolMilestoneSpeakLine('Edit ui/js/auth-bootstrap.js', {
        operatorPrompt: 'fix login redirect',
      }),
    ).toBe('Updating auth-bootstrap.js — fix login redirect');
  });

  it('explains shell commands with OTA awareness', () => {
    expect(
      toolMilestoneSpeakLine('Shell eas update --branch production', {
        operatorPrompt: 'run production OTA',
      }),
    ).toBe('Running the production OTA — run production OTA');
  });

  it('explains research searches', () => {
    expect(toolMilestoneSpeakLine('Axon research search cursor cli')).toBe(
      'Searching for cursor cli.',
    );
  });
});

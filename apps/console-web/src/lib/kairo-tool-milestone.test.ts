import { describe, expect, it } from 'vitest';

import { toolMilestoneSpeakLine } from './kairo-tool-milestone';

describe('kairo tool milestone', () => {
  it('explains read tools with a short file name', () => {
    expect(
      toolMilestoneSpeakLine(
        'Read services/control-plane/app/research/availability.py',
      ),
    ).toBe("I'm opening availability.py to review what we're working with.");
  });

  it('explains edit tools', () => {
    expect(toolMilestoneSpeakLine('Edit ui/js/auth-bootstrap.js')).toBe(
      "I'm updating auth-bootstrap.js.",
    );
  });

  it('explains shell commands', () => {
    expect(toolMilestoneSpeakLine('Shell npm run verify:contracts')).toBe(
      "I'm running npm run verify:contracts in the terminal.",
    );
  });

  it('explains research searches', () => {
    expect(toolMilestoneSpeakLine('Axon research search cursor cli')).toBe(
      "I'm searching for cursor cli.",
    );
  });
});

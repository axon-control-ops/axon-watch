import { describe, expect, it } from 'vitest';

import {
  buildAgentTerminalMirrorScrollback,
  buildAgentTerminalMirrorText,
  findAgentTerminalMirrorSegment,
  terminalMirrorSignature,
} from './agent-terminal-mirror';

describe('agent terminal mirror', () => {
  it('prefers the open terminal segment', () => {
    const segment = findAgentTerminalMirrorSegment(
      [
        ':::terminal git status',
        'ok',
        ':::',
        ':::terminal npm test',
        'running',
      ].join('\n'),
    );
    expect(segment).toMatchObject({
      kind: 'terminal',
      command: 'npm test',
      open: true,
    });
  });

  it('falls back to the latest closed terminal', () => {
    const segment = findAgentTerminalMirrorSegment(
      [':::terminal git status', 'ok', ':::', ':::terminal npm test', 'done', ':::'].join('\n'),
    );
    expect(segment).toMatchObject({
      command: 'npm test',
      output: 'done',
      open: false,
    });
  });

  it('builds a Cursor-like shell snapshot', () => {
    expect(
      buildAgentTerminalMirrorText({
        kind: 'terminal',
        command: 'npm test',
        output: '',
        open: true,
      }),
    ).toBe('$ npm test\nrunning…\n');

    expect(
      buildAgentTerminalMirrorText({
        kind: 'terminal',
        command: 'npm test',
        output: 'ok\n',
        open: false,
      }),
    ).toBe('$ npm test\nok\n');
  });

  it('builds scrollback for OTA retries so prior output stays in the dock', () => {
    const transcript = [
      ':::terminal npm run ota',
      'Release guard: dirty tree',
      ':::',
      ':::terminal RELEASE_GUARD_ALLOW_DIRTY=1 npm run ota',
    ].join('\n');

    expect(buildAgentTerminalMirrorScrollback(transcript)).toBe(
      [
        '$ npm run ota',
        'Release guard: dirty tree',
        '',
        '$ RELEASE_GUARD_ALLOW_DIRTY=1 npm run ota',
        'running…',
      ].join('\n') + '\n',
    );
  });

  it('tracks terminal output length even when prose follows the shell block', () => {
    const before = [':::terminal npm run ota', 'line 1', ':::', 'Done.'].join('\n');
    const after = [':::terminal npm run ota', 'line 1', 'line 2', ':::', 'Done.'].join('\n');
    expect(terminalMirrorSignature(before)).not.toBe(terminalMirrorSignature(after));
  });
});

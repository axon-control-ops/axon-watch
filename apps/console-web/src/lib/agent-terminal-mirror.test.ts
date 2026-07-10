import { describe, expect, it } from 'vitest';

import {
  buildAgentTerminalMirrorText,
  findAgentTerminalMirrorSegment,
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
});

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

  it('mirrors OTA status polls as compact job receipts without zshenv noise', () => {
    const text = buildAgentTerminalMirrorText({
      kind: 'terminal',
      command: 'axon-agent-terminal-job --status agent-job-792f81463677',
      output: [
        '/home/edp/.zshenv:.:1: no such file or directory: "/home/edp/.cargo/env"',
        JSON.stringify({
          job_id: 'agent-job-792f81463677',
          status: 'running',
          command: 'npm run ota:canary',
        }),
      ].join('\n'),
      open: false,
    });
    expect(text).toContain('$ npm run ota:canary');
    expect(text).toContain('# running · agent-job-792f81463677 · npm run ota:canary');
    expect(text).toContain('Status: running');
    expect(text).not.toMatch(/zshenv/);
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
        '$ npm run ota',
        'running…',
      ].join('\n') + '\n',
    );
  });

  it('keeps a recent terminal window by default so long OTA threads stay responsive', () => {
    const transcript = Array.from(
      { length: 12 },
      (_, index) => `:::terminal command-${index}\noutput-${index}\n:::`,
    ).join('\n');

    const scrollback = buildAgentTerminalMirrorScrollback(transcript);
    expect(scrollback).not.toContain('$ command-0\noutput-0');
    expect(scrollback).toContain('$ command-6\noutput-6');
    expect(scrollback).toContain('$ command-11\noutput-11');
    expect(buildAgentTerminalMirrorScrollback(transcript, { maxSegments: 12 })).toContain(
      '$ command-0\noutput-0',
    );
  });

  it('tracks terminal output length even when prose follows the shell block', () => {
    const before = [':::terminal npm run ota', 'line 1', ':::', 'Done.'].join('\n');
    const after = [':::terminal npm run ota', 'line 1', 'line 2', ':::', 'Done.'].join('\n');
    expect(terminalMirrorSignature(before)).not.toBe(terminalMirrorSignature(after));
  });
});

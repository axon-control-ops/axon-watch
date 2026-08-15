import { describe, expect, it } from 'vitest';

import {
  AGENT_TERMINAL_JOB_OUTPUT_CAP,
  buildAgentTerminalJobView,
  capTerminalJobOutput,
  looksLikeAgentTerminalJob,
  prioritizeTerminalJobTail,
  shortenTerminalCommandLabel,
  stripTerminalJobNoise,
} from './agent-terminal-job-view';

describe('agent-terminal-job-view', () => {
  it('strips zshenv / cargo noise from status polls', () => {
    const cleaned = stripTerminalJobNoise(
      [
        '/home/edp/.zshenv:.:1: no such file or directory: "/home/edp/.cargo/env"',
        '{',
        '  "job_id": "agent-job-792f81463677",',
        '  "status": "running"',
        '}',
      ].join('\n'),
    );
    expect(cleaned).not.toMatch(/zshenv/);
    expect(cleaned).toContain('"job_id"');
  });

  it('formats status JSON into a compact job card view', () => {
    const view = buildAgentTerminalJobView({
      command: 'axon-agent-terminal-job --status agent-job-792f81463677',
      output: [
        '/home/edp/.zshenv:.:1: no such file or directory: "/home/edp/.cargo/env"',
        JSON.stringify(
          {
            job_id: 'agent-job-792f81463677',
            workspace_id: 'workspace_dashpro',
            status: 'running',
            command: 'env RELEASE_GUARD_ALLOW_DIRTY=1 npm run ota:canary',
          },
          null,
          2,
        ),
      ].join('\n'),
    });
    expect(view.kind).toBe('job_status');
    expect(view.isOta).toBe(true);
    expect(view.jobId).toBe('agent-job-792f81463677');
    expect(view.status).toBe('running');
    expect(view.commandLabel).toBe('npm run ota:canary');
    expect(view.displayOutput).toContain('Status: running');
    expect(view.displayOutput).not.toMatch(/zshenv/);
    expect(view.headline).toContain('running');
  });

  it('detects live axon-job streams and keeps progress tail', () => {
    const lines = [
      '# axon-job:agent-job-792f81463677',
      'starting…',
      ...Array.from({ length: 30 }, (_, i) => `noise line ${i}`),
      '[expo-cli] iOS ./index.js ████████ 85.3% (5758/6234)',
      '[expo-cli] Android ./index.js ████████ 98.9% (6141/6441)',
      'Exporting...',
    ];
    const view = buildAgentTerminalJobView({
      command: 'env RELEASE_GUARD_ALLOW_DIRTY=1 npm run ota:canary',
      output: lines.join('\n'),
    });
    expect(view.kind).toBe('job_stream');
    expect(view.isOta).toBe(true);
    expect(view.jobId).toBe('agent-job-792f81463677');
    expect(view.displayOutput).toContain('85.3%');
    expect(view.displayOutput).toContain('Exporting');
    expect(view.displayOutput).toContain('# axon-job:agent-job-792f81463677');
    expect(view.displayOutput.split('\n').length).toBeLessThanOrEqual(40);
  });

  it('prefers server-tracked job status over regex-parsed stream text', () => {
    const view = buildAgentTerminalJobView({
      command: 'npm run ota:canary',
      output: '# axon-job:agent-job-1\nstatus=running\nFinished.',
      serverStatus: 'completed',
    });
    expect(view.kind).toBe('job_stream');
    expect(view.jobId).toBe('agent-job-1');
    expect(view.status).toBe('completed');
    expect(view.headline).toContain('completed');
  });

  it('shortens env-prefixed OTA commands', () => {
    expect(
      shortenTerminalCommandLabel(
        'RELEASE_GUARD_ALLOW_DIRTY=1 RELEASE_GUARD_ALLOW_ANY_BRANCH=1 npm run ota:canary',
      ),
    ).toBe('npm run ota:canary');
  });

  it('prioritizeTerminalJobTail keeps marker + progress', () => {
    const text = [
      '# axon-job:agent-job-1',
      ...Array.from({ length: 50 }, (_, i) => `line ${i}`),
      '[expo-cli] Android 90%',
    ].join('\n');
    const tail = prioritizeTerminalJobTail(text, 20);
    expect(tail).toContain('# axon-job:agent-job-1');
    expect(tail).toContain('90%');
  });

  it('skips heavy job formatting for ordinary shell cards', () => {
    expect(looksLikeAgentTerminalJob('git status --short', ' M README.md')).toBe(false);
    expect(
      looksLikeAgentTerminalJob(
        'axon-agent-terminal-job --status agent-job-1',
        '{"job_id":"agent-job-1","status":"running"}',
      ),
    ).toBe(true);
    const plain = buildAgentTerminalJobView({
      command: 'export TERM=dumb; python3 - <<\'PY\'\nprint(1)\nPY',
      output: '1\n',
    });
    expect(plain.kind).toBe('shell');
    expect(plain.headline).toBeNull();
  });

  it('caps huge OTA streams before formatting so the UI stays responsive', () => {
    const huge = `${'# axon-job:agent-job-big\n'}${'x'.repeat(AGENT_TERMINAL_JOB_OUTPUT_CAP + 20_000)}`;
    expect(capTerminalJobOutput(huge).length).toBe(AGENT_TERMINAL_JOB_OUTPUT_CAP);
    const view = buildAgentTerminalJobView({
      command: 'npm run ota:canary',
      output: huge,
    });
    expect(view.kind).toBe('job_stream');
    expect(view.jobId).toBe('agent-job-big');
    expect(view.displayOutput.length).toBeLessThanOrEqual(AGENT_TERMINAL_JOB_OUTPUT_CAP);
  });

  it('cleans npm test output for compact terminal cards', () => {
    const view = buildAgentTerminalJobView({
      command: 'npm test -- tests/unit/services/staffVisibility.test.ts',
      output: [
        '\u001b[1A\u001b[999D\u001b[K\u001b[1mTest Suites:\u001b[22m \u001b[32m1 passed\u001b[39m',
        'PASS tests/unit/services/staffVisibility.test.ts',
        'Test Suites: 1 passed, 1 total',
        'Tests:       9 passed, 9 total',
      ].join('\n'),
    });
    expect(view.displayOutput).toContain('PASS tests/unit/services/staffVisibility.test.ts');
    expect(view.displayOutput).toContain('9 passed, 9 total');
    expect(view.displayOutput).not.toMatch(/\[1A|\[32m/);
  });
});

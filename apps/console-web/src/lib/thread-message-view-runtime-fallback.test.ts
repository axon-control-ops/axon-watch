import { describe, expect, it } from 'vitest';

import {
  agentContentLooksLikeErrorDump,
  agentContentLooksLikeRuntimeFallback,
} from './thread-message-view';

// These are verbatim outputs of
// services/control-plane/app/cli_runtime/runtime_failure.py::fallback_reply.
// tests/test_runtime_fallback_marker_contract.py asserts the Python side still
// produces exactly these shapes, so the two suites fail together if the copy
// is reworded on only one side.
const REAL_FALLBACKS = [
  'Lane B (agent) failed on Cursor CLI (local): maximum recursion depth exceeded. Check Runtime status, then retry.',
  'Lane B (ask) failed on Claude Code CLI: Not logged in · Please run /login. Run `cursor agent login` on the host or unlock `/vault`, then retry.',
  "Lane B (agent) could not start on Cursor CLI (local): ActionRequiredError: You've hit your usage limit. Check Cursor Usage, then retry.",
  'Lane B (agent) could not start — Cursor unpaid invoice blocked the agent: ActionRequiredError: You have an unpaid invoice. Visit cursor.com/dashboard.',
  "Lane B (plan) could not start — Cursor usage limits blocked the agent: You've hit your usage limit. Check Cursor Usage, then retry.",
  'Lane B (debug) cannot start because no CLI runtime is ready: Cursor auth probe timed out. Check `cursor agent status` on the host, then retry.',
];

describe('agentContentLooksLikeRuntimeFallback', () => {
  it('flags every real fallback_reply shape', () => {
    for (const text of REAL_FALLBACKS) {
      expect(agentContentLooksLikeRuntimeFallback(text), text).toBe(true);
    }
  });

  it('does not flag ordinary agent answers', () => {
    const answers = [
      'Done — I updated README.md and the tests pass.',
      'I could not start the server because port 8787 was busy.',
      'Lane B is a concept in this repo; here is how it works.',
      '## Summary\n\nThe fix landed cleanly.',
      '',
      '   ',
    ];
    for (const text of answers) {
      expect(agentContentLooksLikeRuntimeFallback(text), text).toBe(false);
    }
  });

  it('is independent of the error-dump heuristic', () => {
    // The whole point: a fallback is plain prose, so the pre-existing
    // error-dump detector never fired on it and it rendered as a normal reply.
    for (const text of REAL_FALLBACKS) {
      expect(agentContentLooksLikeErrorDump(text), text).toBe(false);
    }
  });

  it('tolerates surrounding and collapsed whitespace', () => {
    const text = REAL_FALLBACKS[0];
    expect(agentContentLooksLikeRuntimeFallback(`  ${text}  `)).toBe(true);
    expect(agentContentLooksLikeRuntimeFallback(text.replace(' ', '  '))).toBe(true);
    expect(agentContentLooksLikeRuntimeFallback(`\nLane B (agent)\nfailed on X: y.`)).toBe(true);
  });
});

import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

import { describe, expect, it } from 'vitest';

import {
  explainOperatorAlert,
  normalizeServerAlertExplanation,
  resolveOperatorAlertExplanation,
} from './operator-signal-hints';

type GoldenCase = {
  id: string;
  input: {
    signal_id?: string;
    title?: string;
    summary?: string;
    meta?: Record<string, unknown>;
    pending_approvals?: number;
    reason?: string;
  };
  expect_spoken_contains: string[];
  expect_what_contains: string[];
  expect_agent_do_contains: string[];
};

const goldensPath = join(
  dirname(fileURLToPath(import.meta.url)),
  '../../../../config/operator-alert-explain-goldens.json',
);

const goldens = JSON.parse(readFileSync(goldensPath, 'utf8')) as GoldenCase[];

describe('operator-alert-explain goldens (TS parity)', () => {
  it.each(goldens)('$id matches shared golden expectations', (caseItem) => {
    const explained = explainOperatorAlert({
      signalId: caseItem.input.signal_id,
      title: caseItem.input.title,
      summary: caseItem.input.summary,
      meta: caseItem.input.meta,
      pendingApprovals: caseItem.input.pending_approvals,
      reason: caseItem.input.reason,
    });

    for (const needle of caseItem.expect_spoken_contains) {
      expect(explained.spoken.toLowerCase()).toContain(needle.toLowerCase());
    }
    for (const needle of caseItem.expect_what_contains) {
      expect(explained.what.toLowerCase()).toContain(needle.toLowerCase());
    }
    for (const needle of caseItem.expect_agent_do_contains) {
      expect(explained.agentDo.toLowerCase()).toContain(needle.toLowerCase());
    }
  });

  it('prefers matching server explanation over local heuristics', () => {
    const resolved = resolveOperatorAlertExplanation({
      signalId: 'signal_connector_console_web_unavailable',
      title: 'Console web connector unavailable',
      serverSignalId: 'signal_connector_console_web_unavailable',
      serverReason: 'high_urgency_signal',
      serverExplanation: {
        what: 'Server says the console connection is down.',
        you_do: 'Restart the console service.',
        agent_do: 'Check the console process and restart it.',
        spoken: 'Console connection is down.',
      },
    });

    expect(resolved.what).toBe('Server says the console connection is down.');
    expect(resolved.youDo).toBe('Restart the console service.');
  });

  it('normalizes snake_case server payloads', () => {
    expect(
      normalizeServerAlertExplanation({
        what: 'A',
        you_do: 'B',
        agent_do: 'C',
        spoken: 'D',
      }),
    ).toEqual({ what: 'A', youDo: 'B', agentDo: 'C', spoken: 'D' });
  });
});

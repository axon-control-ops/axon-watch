import { describe, expect, it } from 'vitest';

import {
  DEBUG_REPRODUCE_PROCEED_MESSAGE,
  buildDebugReproduceProceedContent,
  contentHasDebugReproduceMarker,
  extractDebugReproduceRequest,
  parseDebugReproduceSteps,
  sanitizeDebugReproduceSteps,
  shouldShowDebugReproduceBanner,
} from './debug-reproduce-view';

describe('debug-reproduce-view', () => {
  it('parses numbered reproduce steps from a closed marker', () => {
    const content = [
      'Instrumentation is in place.',
      ':::debug-reproduce',
      '1. Open settings',
      '2. Click Save',
      ':::',
    ].join('\n');
    expect(parseDebugReproduceSteps(content)).toEqual(['Open settings', 'Click Save']);
    expect(contentHasDebugReproduceMarker(content)).toBe(true);
  });

  it('strips markdown, drops hypotheses, dedupes, and caps at four actions', () => {
    expect(
      sanitizeDebugReproduceSteps([
        '**H1** — Stream was interrupted',
        'Open the workspace menu',
        'Open the workspace menu',
        '+ **H2** — Folder picker missing',
        'Click **+ New Workspace**',
        'Fill in `project_root`',
        'Submit the form',
        'Watch the NDJSON log file',
        'Extra step five should be dropped',
      ]),
    ).toEqual([
      'Open the workspace menu',
      'Click + New Workspace',
      'Fill in project_root',
      'Submit the form',
    ]);
  });

  it('sanitizes noisy model dumps inside the reproduce block', () => {
    const content = [
      ':::debug-reproduce',
      '1. **H1** — The ID field feels like a secret',
      '2. Open Settings',
      '3. Open Settings',
      '4. Click Save',
      '5. Confirm the toast',
      '6. Check debug-session.ndjson',
      '7. Extra',
      ':::',
    ].join('\n');
    expect(parseDebugReproduceSteps(content)).toEqual([
      'Open Settings',
      'Click Save',
      'Confirm the toast',
      'Extra',
    ]);
  });

  it('ignores marker mentions inside edit diffs and prose', () => {
    const content = [
      'Debug ends the turn with a `:::debug-reproduce` block.',
      ':::edit apps/console-web/src/lib/debug-reproduce-view.ts +3 -0',
      '+const HEADER = ":::debug-reproduce";',
      '+const sample = [',
      '+":::debug-reproduce",',
      '+"1. Click Save",',
      '+":::",',
      '+];',
      ':::',
      'Still waiting for a real top-level pause.',
    ].join('\n');
    expect(parseDebugReproduceSteps(content)).toBeNull();
    expect(contentHasDebugReproduceMarker(content)).toBe(false);
    expect(
      extractDebugReproduceRequest({
        streaming: false,
        messages: [{ message_id: 'm-noise', role: 'agent', content }],
      }),
    ).toBeNull();
  });

  it('extracts the latest agent reproduce request when idle', () => {
    const request = extractDebugReproduceRequest({
      streaming: false,
      messages: [
        {
          message_id: 'm1',
          role: 'agent',
          content: ':::debug-reproduce\n1. Click the broken button\n:::',
        },
      ],
    });
    expect(request?.messageId).toBe('m1');
    expect(request?.steps).toEqual(['Click the broken button']);
    expect(request?.source).toBe('marker');
  });

  it('does not use prose heuristics for reproduce pauses', () => {
    expect(
      extractDebugReproduceRequest({
        streaming: false,
        messages: [
          {
            message_id: 'm-heuristic',
            role: 'agent',
            content: 'Please reproduce the bug using the steps above, then proceed again.',
          },
        ],
      }),
    ).toBeNull();
  });

  it('hides the banner while streaming or after dismiss', () => {
    const request = {
      messageId: 'm1',
      steps: ['Reproduce'],
      source: 'marker' as const,
    };
    expect(
      shouldShowDebugReproduceBanner({
        composerMode: 'debug',
        request,
        dismissedMessageId: null,
      }),
    ).toBe(true);
    expect(
      shouldShowDebugReproduceBanner({
        composerMode: 'debug',
        request,
        dismissedMessageId: 'm1',
      }),
    ).toBe(false);
    expect(
      shouldShowDebugReproduceBanner({
        composerMode: 'agent',
        linkedRunMode: 'debug',
        request,
        dismissedMessageId: null,
      }),
    ).toBe(true);
    expect(
      extractDebugReproduceRequest({
        streaming: true,
        messages: [
          {
            message_id: 'm1',
            role: 'agent',
            content: ':::debug-reproduce\n1. Step\n:::',
          },
        ],
      }),
    ).toBeNull();
  });

  it('exports a proceed follow-up that points at the debug log', () => {
    expect(DEBUG_REPRODUCE_PROCEED_MESSAGE).toContain('.axon/debug-session.ndjson');
  });

  it('keeps the operator reply when building a proceed follow-up', () => {
    expect(buildDebugReproduceProceedContent('')).toBe(DEBUG_REPRODUCE_PROCEED_MESSAGE);
    expect(buildDebugReproduceProceedContent('  H1 looks confirmed  ')).toContain(
      'H1 looks confirmed',
    );
    expect(buildDebugReproduceProceedContent('H1 looks confirmed')).toContain(
      '.axon/debug-session.ndjson',
    );
    expect(
      buildDebugReproduceProceedContent(
        "I've reproduced the bug. Please read `.axon/debug-session.ndjson`.",
      ),
    ).toContain('.axon/debug-session.ndjson');
  });
});

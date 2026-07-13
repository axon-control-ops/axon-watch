import { describe, expect, it } from 'vitest';

import {
  DEBUG_REPRODUCE_PROCEED_MESSAGE,
  contentHasDebugReproduceMarker,
  extractDebugReproduceRequest,
  parseDebugReproduceSteps,
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
});

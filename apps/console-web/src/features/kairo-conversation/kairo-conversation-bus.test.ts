import { afterEach, describe, expect, it, vi } from 'vitest';

import {
  registerKairoConversationSubmit,
  resetKairoConversationSubmitBusForTests,
  submitKairoConversationTranscript,
} from './kairo-conversation-bus';

describe('kairo conversation bus', () => {
  afterEach(() => {
    resetKairoConversationSubmitBusForTests();
  });

  it('delivers directly when a submit handler is registered', async () => {
    const handler = vi.fn(async () => {});
    registerKairoConversationSubmit(handler);

    await submitKairoConversationTranscript('hey VAXON', {
      voiceCaptureMode: 'hands_free',
    });

    expect(handler).toHaveBeenCalledWith('hey VAXON', {
      voiceCaptureMode: 'hands_free',
    });
  });

  it('queues accepted transcripts until a handler is registered', async () => {
    await submitKairoConversationTranscript('git status', {
      voiceCaptureMode: 'manual',
    });

    const handler = vi.fn(async () => {});
    registerKairoConversationSubmit(handler);
    await Promise.resolve();

    expect(handler).toHaveBeenCalledWith('git status', {
      voiceCaptureMode: 'manual',
    });
  });

  it('restores the previous handler when the latest one unregisters', async () => {
    const fallback = vi.fn(async () => {});
    const unregisterFallback = registerKairoConversationSubmit(fallback);
    const top = vi.fn(async () => {});
    const unregisterTop = registerKairoConversationSubmit(top);

    await submitKairoConversationTranscript('first');
    unregisterTop();
    await submitKairoConversationTranscript('second');

    expect(top).toHaveBeenCalledWith('first', undefined);
    expect(fallback).toHaveBeenCalledWith('second', undefined);

    unregisterFallback();
  });
});

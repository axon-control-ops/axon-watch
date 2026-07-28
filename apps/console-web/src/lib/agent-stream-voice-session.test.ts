import { describe, expect, it, vi } from 'vitest';

import { createAgentStreamIncrementalState } from './agent-stream-incremental';
import { handleAgentStreamVoiceDelta } from './agent-stream-voice-session';
import type { ChatStreamVoiceNarration } from './chat-stream-voice-narration';
import type { NarrationMilestone } from './kairo-agent-narration';

describe('handleAgentStreamVoiceDelta', () => {
  it('speaks completed thinking and skips canned tool lines in the same delta', () => {
    const streamIncremental = createAgentStreamIncrementalState();
    const maybeSpeakThinkingBlock = vi.fn(() => true);
    const narrateAgentMilestone = vi.fn(
      (_milestone: NarrationMilestone, _options?: { preserveQueue?: boolean }) => undefined,
    );
    const voiceNarration = {
      toolNarrationEnabled: true,
      progressNarrator: null,
      agentMilestoneNarrator: null,
      answerNarrator: null,
      speakStartBookend: vi.fn(() => false),
      maybeSpeakThinkingBlock,
      narrateAgentMilestone,
      narrateProgress: vi.fn(),
      narrateCompletion: vi.fn(),
      narrateFailure: vi.fn(),
    } satisfies ChatStreamVoiceNarration;

    const content =
      ':::thinking\nI will check the enrollment confirmation UI next.\n:::\n\n:::tool Read app/enroll.tsx\n';

    handleAgentStreamVoiceDelta({
      voiceNarration,
      streamIncremental,
      content,
      fullAccessNarration: false,
      patchActivity: vi.fn(),
    });

    expect(maybeSpeakThinkingBlock).toHaveBeenCalledWith(
      'I will check the enrollment confirmation UI next.',
    );
    expect(
      narrateAgentMilestone.mock.calls.some((call) =>
        String(call[0]?.key ?? '').startsWith('tool:'),
      ),
    ).toBe(false);
    expect(
      narrateAgentMilestone.mock.calls.some((call) =>
        String(call[0]?.key ?? '').startsWith('thinking:'),
      ),
    ).toBe(false);
  });

  it('still narrates tools when no thinking block spoke', () => {
    const streamIncremental = createAgentStreamIncrementalState();
    const maybeSpeakThinkingBlock = vi.fn(() => false);
    const narrateAgentMilestone = vi.fn();
    const voiceNarration = {
      toolNarrationEnabled: true,
      progressNarrator: null,
      agentMilestoneNarrator: null,
      answerNarrator: null,
      speakStartBookend: vi.fn(() => false),
      maybeSpeakThinkingBlock,
      narrateAgentMilestone,
      narrateProgress: vi.fn(),
      narrateCompletion: vi.fn(),
      narrateFailure: vi.fn(),
    } satisfies ChatStreamVoiceNarration;

    handleAgentStreamVoiceDelta({
      voiceNarration,
      streamIncremental,
      content: ':::tool Read app/enroll.tsx\n',
      fullAccessNarration: false,
      patchActivity: vi.fn(),
    });

    expect(
      narrateAgentMilestone.mock.calls.some((call) =>
        String(call[0]?.key ?? '').startsWith('tool:'),
      ),
    ).toBe(true);
  });
});

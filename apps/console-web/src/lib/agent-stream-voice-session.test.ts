import { describe, expect, it, vi } from 'vitest';

import { createAgentStreamIncrementalState } from './agent-stream-incremental';
import { handleAgentStreamVoiceDelta } from './agent-stream-voice-session';
import type { ChatStreamVoiceNarration } from './chat-stream-voice-narration';
import type { NarrationMilestone } from './kairo-agent-narration';

describe('handleAgentStreamVoiceDelta', () => {
  it('speaks completed thinking before tool milestones and preserves the queue', () => {
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
    expect(narrateAgentMilestone).toHaveBeenCalled();
    const firstToolCall = narrateAgentMilestone.mock.calls.find((call) =>
      String(call[0]?.key ?? '').startsWith('tool:'),
    );
    expect(firstToolCall?.[1]).toEqual({ preserveQueue: true });
    expect(
      narrateAgentMilestone.mock.calls.some((call) =>
        String(call[0]?.key ?? '').startsWith('thinking:'),
      ),
    ).toBe(false);
  });
});

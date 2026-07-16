import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('./kairo-agent-milestone-narrator', () => ({
  createKairoAgentMilestoneNarrator: vi.fn(() => ({
    narrate: vi.fn(),
  })),
}));

vi.mock('./kairo-progress-narrator', () => ({
  createKairoProgressNarrator: vi.fn(() => ({
    narrate: vi.fn(),
  })),
}));

import { createKairoAgentMilestoneNarrator } from './kairo-agent-milestone-narrator';
import { createChatStreamVoiceNarration } from './chat-stream-voice-narration';

describe('createChatStreamVoiceNarration', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('creates tool narrators for agent but not answer narrators', () => {
    const voice = createChatStreamVoiceNarration({
      composerMode: 'agent',
      messageId: 'msg_1',
      sessionId: () => 'session',
      workspaceId: () => 'workspace_a',
      narration: () => 'minimal',
      voiceDeliveryAllowed: () => true,
      operatorPrompt: () => 'fix it',
      fullAccess: () => false,
    });

    expect(voice.toolNarrationEnabled).toBe(true);
    expect(voice.agentMilestoneNarrator).not.toBeNull();
    expect(voice.answerNarrator).toBeNull();
    expect(createKairoAgentMilestoneNarrator).toHaveBeenCalledTimes(1);
  });

  it('speaks ask/plan final answers without tool milestones', () => {
    const voice = createChatStreamVoiceNarration({
      composerMode: 'ask',
      messageId: 'msg_2',
      sessionId: () => 'session',
      workspaceId: () => 'workspace_a',
      narration: () => 'minimal',
      voiceDeliveryAllowed: () => true,
      operatorPrompt: () => 'what needs attention?',
      fullAccess: () => false,
    });

    expect(voice.toolNarrationEnabled).toBe(false);
    expect(voice.agentMilestoneNarrator).toBeNull();
    expect(voice.answerNarrator).not.toBeNull();

    voice.narrateCompletion('DashPro has one critical signal waiting in Attention.');
    expect(voice.answerNarrator?.narrate).toHaveBeenCalledWith(
      expect.objectContaining({
        key: 'done',
        verbatim: true,
        message: expect.stringContaining('DashPro'),
      }),
    );

    voice.narrateProgress({
      event_key: 'tool:0',
      event_type: 'tool',
    });
    expect(voice.progressNarrator).toBeNull();
  });

  it('stays quiet for ask/plan when narration is off', () => {
    const voice = createChatStreamVoiceNarration({
      composerMode: 'plan',
      messageId: 'msg_3',
      sessionId: () => 'session',
      workspaceId: () => 'workspace_a',
      narration: () => 'off',
      voiceDeliveryAllowed: () => true,
      operatorPrompt: () => 'draft a plan',
      fullAccess: () => false,
    });

    voice.narrateCompletion('Here is a three-step plan.');
    expect(voice.answerNarrator?.narrate).not.toHaveBeenCalled();
  });
});

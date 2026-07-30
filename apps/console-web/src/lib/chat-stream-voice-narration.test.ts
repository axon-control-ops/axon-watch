import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('./kairo-agent-milestone-narrator', () => ({
  createKairoAgentMilestoneNarrator: vi.fn(() => ({
    narrate: vi.fn(),
    cancel: vi.fn(),
  })),
}));

vi.mock('./kairo-progress-narrator', () => ({
  createKairoProgressNarrator: vi.fn(() => ({
    narrate: vi.fn(),
    cancel: vi.fn(),
  })),
}));

vi.mock('./kairo-voice-queue', () => ({
  dropWaitingKairoNarration: vi.fn(),
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
      narrateToolProgress: () => false,
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
      narrateToolProgress: () => false,
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
      narrateToolProgress: () => false,
      voiceDeliveryAllowed: () => true,
      operatorPrompt: () => 'draft a plan',
      fullAccess: () => false,
    });

    voice.narrateCompletion('Here is a three-step plan.');
    expect(voice.answerNarrator?.narrate).not.toHaveBeenCalled();
  });

  it('speaks the same thread ack on start, not a forced receipts line or persona meta', () => {
    const voice = createChatStreamVoiceNarration({
      composerMode: 'agent',
      messageId: 'msg_4',
      sessionId: () => 'session',
      workspaceId: () => 'workspace_edudashpro_school',
      narration: () => 'minimal',
      narrateToolProgress: () => false,
      voiceDeliveryAllowed: () => true,
      operatorPrompt: () => 'retry the bounded continuous shift',
      fullAccess: () => true,
      speaker: () => ({
        kind: 'employee',
        id: 'employee-lindi',
        name: 'Lindi',
        roleLabel: 'Lead',
      }),
    });

    expect(voice.speakStartBookend()).toBe(true);
    expect(voice.agentMilestoneNarrator?.narrate).toHaveBeenCalledWith(
      expect.objectContaining({
        key: 'start',
        verbatim: true,
        message: 'Working that now, Sir King.',
      }),
    );

    voice.maybeSpeakThinkingBlock(
      'Assuming the Lindi persona for the EDP Excellence workspace. Reviewing her last shift receipts.',
    );
    expect(voice.agentMilestoneNarrator?.narrate).toHaveBeenCalledTimes(1);
  });

  it('skips post-IDLE progress openers when mid-run thinking already carried intent', () => {
    const voice = createChatStreamVoiceNarration({
      composerMode: 'agent',
      messageId: 'msg_6',
      sessionId: () => 'session',
      workspaceId: () => 'workspace_dashpro',
      narration: () => 'minimal',
      narrateToolProgress: () => false,
      voiceDeliveryAllowed: () => true,
      operatorPrompt: () => 'fix the payments card',
      fullAccess: () => true,
      speaker: () => ({
        kind: 'employee',
        id: 'employee-priya',
        name: 'Priya',
        roleLabel: 'Frontend',
      }),
    });

    expect(voice.speakStartBookend()).toBe(true);
    vi.mocked(voice.agentMilestoneNarrator!.narrate).mockClear();

    voice.narrateCompletion(
      'Reading the parent dashboard survey payments wiring and the selected-child card styles next, then fix that card layout and produce a clear dashboard layout preview.',
    );
    expect(voice.agentMilestoneNarrator?.narrate).not.toHaveBeenCalled();
  });

  it('still speaks a Confidence close-out after thinking carried intent', () => {
    const voice = createChatStreamVoiceNarration({
      composerMode: 'agent',
      messageId: 'msg_7',
      sessionId: () => 'session',
      workspaceId: () => 'workspace_dashpro',
      narration: () => 'minimal',
      narrateToolProgress: () => false,
      voiceDeliveryAllowed: () => true,
      operatorPrompt: () => 'fix the payments card',
      fullAccess: () => true,
    });

    expect(voice.speakStartBookend()).toBe(true);
    vi.mocked(voice.agentMilestoneNarrator!.narrate).mockClear();

    voice.narrateCompletion(
      'Reading the wiring next.\n\nCritical Review: payments card layout is restored.\n\nConfidence: 8/10',
    );
    expect(voice.agentMilestoneNarrator?.narrate).toHaveBeenCalledWith(
      expect.objectContaining({
        key: 'done',
        message: expect.stringMatching(/Critical Review|Confidence/i),
      }),
    );
  });

  it('prefers sanitized model live text over the ack when thinking arrives first', () => {
    const voice = createChatStreamVoiceNarration({
      composerMode: 'agent',
      messageId: 'msg_5',
      sessionId: () => 'session',
      workspaceId: () => 'workspace_edudashpro_school',
      narration: () => 'minimal',
      narrateToolProgress: () => false,
      voiceDeliveryAllowed: () => true,
      operatorPrompt: () => 'retry the bounded continuous shift',
      fullAccess: () => true,
      speaker: () => ({
        kind: 'employee',
        id: 'employee-lindi',
        name: 'Lindi',
        roleLabel: 'Lead',
      }),
    });

    expect(
      voice.maybeSpeakThinkingBlock(
        'Assuming the Lindi persona. Reviewing my last shift receipts and planning docs.',
      ),
    ).toBe(true);
    expect(voice.agentMilestoneNarrator?.narrate).toHaveBeenCalledWith(
      expect.objectContaining({
        key: 'start',
        verbatim: true,
        message: 'Reviewing my last shift receipts and planning docs.',
      }),
    );
  });
});

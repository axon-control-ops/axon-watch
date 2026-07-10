import { beforeEach, describe, expect, it, vi } from 'vitest';

const postKairoConverse = vi.fn();
const handoffSignalToIde = vi.fn();
const speakKairoConversationLine = vi.fn().mockResolvedValue(undefined);
const submitOperatorCommandContent = vi.fn();

vi.mock('../../lib/kairo-converse-client', () => ({
  postKairoConverse: (...args: unknown[]) => postKairoConverse(...args),
}));

vi.mock('../../stores/shell', () => ({
  useShellStore: () => ({
    workspaces: [],
    currentWorkspace: { workspace_id: 'workspace_dashpro' },
    inboxItems: [],
    operatorBriefing: {
      top_signals: [
        {
          signal_id: 'signal_monitor_dashpro_sentry_recent_issues_warning',
          workspace_id: 'workspace_dashpro',
          title: 'Sentry spike in DashPro',
          summary: '3 unresolved issues',
          severity: 'high',
        },
      ],
    },
    operatorPresenceSettings: { privacy_mode: false, hands_free_enabled: false },
    handoffSignalToIde,
    speakKairoConversationLine,
    submitOperatorCommandContent,
    focusAttentionSidebar: vi.fn(),
    focusKairoBriefing: vi.fn(),
    setOperatorCenterView: vi.fn(),
    setCurrentWorkspace: vi.fn(),
  }),
}));

vi.mock('./use-kairo-speech-capture', () => ({
  useKairoSpeechCapture: () => ({
    isSupported: { value: false },
    isListening: { value: false },
    start: vi.fn(),
    stop: vi.fn(),
  }),
}));

vi.mock('./use-kairo-voice-interrupt', () => ({
  useKairoVoiceInterrupt: () => undefined,
}));

describe('conversation handoff order', () => {
  beforeEach(() => {
    postKairoConverse.mockReset();
    handoffSignalToIde.mockReset();
    speakKairoConversationLine.mockReset().mockResolvedValue(undefined);
  });

  it('calls postKairoConverse before client handoff and prefers server action', async () => {
    postKairoConverse.mockResolvedValue({
      turn_kind: 'action',
      reply: 'Handing this off to the IDE now.',
      source: 'template',
      command_content: null,
      requires_confirmation: null,
      action: {
        type: 'handoff_signal',
        signal_id: 'signal_monitor_dashpro_sentry_recent_issues_warning',
        target_workspace_id: 'workspace_dashpro',
        task: 'Investigate signal "Sentry spike in DashPro": 3 unresolved issues',
      },
      artifacts: [],
    });

    const { useKairoConversation } = await import('./use-kairo-conversation');
    const { submitTurn, draft } = useKairoConversation();
    draft.value = 'hand it off';
    await submitTurn();
    await vi.waitFor(() => {
      expect(handoffSignalToIde).toHaveBeenCalled();
    });

    expect(postKairoConverse).toHaveBeenCalledTimes(1);
    expect(handoffSignalToIde).toHaveBeenCalledWith(
      expect.objectContaining({
        signal_id: 'signal_monitor_dashpro_sentry_recent_issues_warning',
        workspace_id: 'workspace_dashpro',
      }),
    );
  });
});

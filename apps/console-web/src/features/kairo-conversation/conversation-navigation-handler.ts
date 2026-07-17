import { canonicalWorkspaceLabel } from '../../lib/kairo-entity-labels';
import type { KairoVoiceCaptureMode } from '../../lib/kairo-voice-gate';
import type { useShellStore } from '../../stores/shell';
import { setBrainGalaxyConversationFocus } from '../brain-galaxy/brain-galaxy-focus';
import {
  resolveConversationNavigationIntent,
  workspaceGalaxyNodeId,
  type ConversationNavigationIntent,
} from './conversation-intents';
import { clearBriefingSurfaceOffer } from './conversation-briefing-surface';

type ShellStore = ReturnType<typeof useShellStore>;

export function resolveKairoConversationNavigationIntent(
  content: string,
  shell: ShellStore,
): ConversationNavigationIntent | null {
  return resolveConversationNavigationIntent(
    content,
    shell.workspaces.map((workspace) => ({
      workspace_id: workspace.workspace_id,
      display_name: canonicalWorkspaceLabel(
        workspace.workspace_id,
        workspace.display_name ?? workspace.workspace_id,
      ),
    })),
  );
}

export async function applyKairoConversationNavigationIntent(input: {
  shell: ShellStore;
  navIntent: ConversationNavigationIntent;
  deliverVoiceReply: (line: string, voiceCaptureMode?: KairoVoiceCaptureMode) => Promise<void>;
  voiceCaptureMode?: KairoVoiceCaptureMode;
  resetDraftState: () => void;
}): Promise<void> {
  if (input.navIntent.kind === 'focus_attention') {
    input.shell.focusAttentionSidebar();
  } else if (input.navIntent.kind === 'focus_briefing') {
    clearBriefingSurfaceOffer();
    input.shell.focusKairoBriefing();
  } else if (input.navIntent.kind === 'focus_workspace' && input.navIntent.workspaceId) {
    input.shell.setOperatorCenterView('graph');
    input.shell.setCurrentWorkspace(input.navIntent.workspaceId);
    const label = canonicalWorkspaceLabel(
      input.navIntent.workspaceId,
      input.shell.workspaces.find(
        (workspace) => workspace.workspace_id === input.navIntent.workspaceId,
      )?.display_name ?? input.navIntent.workspaceId,
    );
    setBrainGalaxyConversationFocus({
      nodeId: workspaceGalaxyNodeId(input.navIntent.workspaceId),
      workspaceId: input.navIntent.workspaceId,
      signalId: null,
      label,
    });
  } else if (input.navIntent.kind === 'switch_center_view' && input.navIntent.centerView) {
    input.shell.setOperatorCenterView(input.navIntent.centerView);
  }
  input.resetDraftState();
  await input.deliverVoiceReply(input.navIntent.reply, input.voiceCaptureMode);
}

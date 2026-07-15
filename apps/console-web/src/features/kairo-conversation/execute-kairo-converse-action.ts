import { applyChatUiAction } from '../../lib/chat-ui-action';
import type { KairoConverseResponse } from '../../lib/kairo-converse-client';
import { useShellStore } from '../../stores/shell';
import { clearBriefingSurfaceOffer } from './conversation-briefing-surface';

type ShellStore = ReturnType<typeof useShellStore>;
type ConverseAction = NonNullable<KairoConverseResponse['action']>;

/** Shared action executor for omnibar + app-voice (no second conversation instance). */
export async function executeKairoConverseAction(
  shell: ShellStore,
  action: ConverseAction,
): Promise<void> {
  if (action.type === 'handoff_signal') {
    await shell.handoffSignalToIde(
      {
        signal_id: action.signal_id,
        workspace_id: action.target_workspace_id,
        title: action.task.replace(/^Investigate signal "/, '').split('"')[0] ?? action.task,
        summary: action.task,
        task: action.task,
      },
      { autoSubmit: true },
    );
    return;
  }
  if (action.type === 'focus_briefing') {
    clearBriefingSurfaceOffer();
    shell.focusKairoBriefing();
    return;
  }
  if (action.type === 'dispatch_command') {
    await shell.submitOperatorCommandContent(action.content);
    return;
  }
  if (action.type === 'move_voice_orb') {
    applyChatUiAction(
      {
        setCurrentWorkspace: shell.setCurrentWorkspace,
        openWorkspaceFile: shell.openWorkspaceFile,
        setVoiceOrbDock: shell.setVoiceOrbDock,
        requestVoiceOrbSmartDodge: shell.requestVoiceOrbSmartDodge,
      },
      action,
    );
  }
}

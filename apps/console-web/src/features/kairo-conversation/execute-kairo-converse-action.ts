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
    const handoffOptions = action.employee_id
      ? { autoSubmit: true, employeeId: action.employee_id }
      : { autoSubmit: true };
    await shell.handoffSignalToIde(
      {
        signal_id: action.signal_id,
        workspace_id: action.target_workspace_id,
        title: action.task.replace(/^Investigate signal "/, '').split('"')[0] ?? action.task,
        summary: action.task,
        task: action.task,
      },
      handoffOptions,
    );
    return;
  }
  if (action.type === 'route_employee') {
    await shell.routeTaskToEmployee({
      targetWorkspaceId: action.target_workspace_id,
      task: action.task,
      employeeId: action.employee_id,
    });
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
    return;
  }
  if (action.type === 'switch_workspace') {
    await shell.loadWorkspaces({ sync: false });
    applyChatUiAction(
      {
        setCurrentWorkspace: shell.setCurrentWorkspace,
        openWorkspaceFile: shell.openWorkspaceFile,
      },
      action,
    );
    // Keep Mission Control selection chrome in sync with VAXON "open workspace".
    if (shell.layoutMode === 'operator') {
      shell.focusMissionControl();
    }
  }
}

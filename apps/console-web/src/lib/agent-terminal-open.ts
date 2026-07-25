/**
 * Open an in-thread `:::terminal` card in the bottom terminal dock.
 *
 * - Live (open/in-flight): stream transcript updates into vaxon (Cursor still owns the process).
 * - Pinned (closed): keep that card's snapshot visible so the agent PTY prompt does not replace it.
 */

import {
  armAgentShellMirror,
  clearAgentShellMirrorForcedText,
  queueAgentShellMirrorText,
} from './agent-shell-mirror-state';
import { buildAgentTerminalMirrorText } from './agent-terminal-mirror';

export type AgentTerminalOpenSegment = {
  command: string;
  output: string;
  open: boolean;
};

export function prepareAgentTerminalOpen(segment: AgentTerminalOpenSegment): 'live' | 'pinned' {
  if (segment.open) {
    clearAgentShellMirrorForcedText();
    armAgentShellMirror();
    return 'live';
  }

  queueAgentShellMirrorText(
    buildAgentTerminalMirrorText({
      kind: 'terminal',
      command: segment.command,
      output: segment.output,
      open: false,
    }),
  );
  return 'pinned';
}

/**
 * Visibility for Cursor-parity "Background" on in-thread agent shell cards.
 *
 * Cursor shows this only while a Shell tool is in-flight (open `:::terminal`
 * block). Pressing it reveals the bottom terminal and mirrors that shell card
 * into the vaxon tab.
 *
 * True process detach (shell continues in a real Axon PTY; agent continues other
 * work) is **not available**: Cursor CLI owns the shell subprocess and exposes
 * no background/detach control in `cursor-agent --help` / stream-json.
 * See docs/planning/AGENT_SHELL_BACKGROUND_DETACH.md.
 */

import { parseAgentTranscriptBlocks } from './agent-transcript-blocks';

/** Honest capability flag — false until Cursor exposes detach protocol. */
export const CURSOR_SHELL_PROCESS_DETACH_AVAILABLE = false;

export type AgentTerminalBackgroundVisibilityInput = {
  canStopIdeAgentRun: boolean;
  /** Open (unclosed) `:::terminal` block = shell tool still running in-thread. */
  terminalBlockRunning: boolean;
};

export function shouldShowAgentTerminalBackgroundControl(
  input: AgentTerminalBackgroundVisibilityInput,
): boolean {
  return input.canStopIdeAgentRun && input.terminalBlockRunning;
}

/** True when the agent transcript still has an unclosed `:::terminal` block. */
export function agentTranscriptHasOpenTerminalBlock(content: string): boolean {
  return parseAgentTranscriptBlocks(content).some(
    (segment) => segment.kind === 'terminal' && segment.open,
  );
}

export function agentTerminalMirrorBadgeLabel(input: {
  segmentOpen: boolean;
  mirrorActive: boolean;
}): string | null {
  if (!input.segmentOpen || !input.mirrorActive) {
    return null;
  }
  return CURSOR_SHELL_PROCESS_DETACH_AVAILABLE ? 'backgrounded' : 'mirrored in vaxon';
}

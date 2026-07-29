/**
 * Visibility for watching an in-thread Cursor-owned shell in the terminal dock.
 *
 * Cursor shows **Move to background** only while a Shell tool call is still
 * running. Finished shell cards are history — Cursor does not offer "run again"
 * on them, and neither do we.
 *
 * The Cursor CLI protocol used by Axon does not expose true process handoff, so
 * Axon labels the available in-flight operation "Watch in terminal" and mirrors
 * the shell without pretending it detached.
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
  if (!input.mirrorActive) {
    return null;
  }
  if (CURSOR_SHELL_PROCESS_DETACH_AVAILABLE && input.segmentOpen) {
    return 'backgrounded';
  }
  return input.segmentOpen ? 'watching in terminal' : 'shown in terminal';
}

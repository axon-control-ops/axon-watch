/**
 * Visibility for Cursor-parity "Background" on in-thread agent shell cards.
 *
 * Cursor shows this only while a Shell tool is in-flight (open `:::terminal`
 * block). Pressing it reveals the bottom terminal and mirrors that shell card
 * into the vaxon tab.
 *
 * True process detach (shell continues in a real PTY; agent continues other
 * work) requires Cursor CLI protocol support — see
 * docs/planning/AGENT_SHELL_BACKGROUND_DETACH.md.
 */

import { parseAgentTranscriptBlocks } from './agent-transcript-blocks';

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

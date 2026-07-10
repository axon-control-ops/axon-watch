/**
 * Visibility for Cursor-parity "Background" on agent terminal runs.
 * Background reveals/focuses the vaxon terminal while the agent keeps running.
 */

export type AgentTerminalBackgroundVisibilityInput = {
  canStopIdeAgentRun: boolean;
  /** Open `:::terminal` transcript block while the agent message is still streaming. */
  terminalBlockRunning?: boolean;
  /** Active bottom-dock session is the agent (vaxon) PTY. */
  agentTerminalFocused?: boolean;
};

export function shouldShowAgentTerminalBackgroundControl(
  input: AgentTerminalBackgroundVisibilityInput,
): boolean {
  if (!input.canStopIdeAgentRun) {
    return false;
  }
  return Boolean(input.terminalBlockRunning || input.agentTerminalFocused);
}

/**
 * Cursor-parity mirror: surface an in-thread `:::terminal` shell card in the
 * bottom vaxon terminal tab when the operator presses Background.
 */

import { parseAgentTranscriptBlocks, type AgentTranscriptSegment } from './agent-transcript-blocks';

export type AgentTerminalMirrorSegment = Extract<AgentTranscriptSegment, { kind: 'terminal' }>;

export function findAgentTerminalMirrorSegment(
  content: string,
): AgentTerminalMirrorSegment | null {
  const terminals = parseAgentTranscriptBlocks(content).filter(
    (segment): segment is AgentTerminalMirrorSegment => segment.kind === 'terminal',
  );
  if (!terminals.length) {
    return null;
  }
  return terminals.find((segment) => segment.open) ?? terminals[terminals.length - 1] ?? null;
}

export function buildAgentTerminalMirrorText(segment: AgentTerminalMirrorSegment): string {
  const lines = [`$ ${segment.command}`];
  const output = segment.output.replace(/\r\n/g, '\n').replace(/^\n+|\n+$/g, '');
  if (output) {
    lines.push(output);
  } else if (segment.open) {
    lines.push('running…');
  }
  return `${lines.join('\n')}\n`;
}

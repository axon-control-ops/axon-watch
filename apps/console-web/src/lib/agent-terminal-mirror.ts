/**
 * Cursor-parity mirror: surface in-thread `:::terminal` shell cards in the
 * bottom vaxon terminal tab when the operator presses Background or a shell
 * tool starts during an agent stream.
 */

import { parseAgentTranscriptBlocks, type AgentTranscriptSegment } from './agent-transcript-blocks';

export type AgentTerminalMirrorSegment = Extract<AgentTranscriptSegment, { kind: 'terminal' }>;

export function listAgentTerminalMirrorSegments(content: string): AgentTerminalMirrorSegment[] {
  return parseAgentTranscriptBlocks(content).filter(
    (segment): segment is AgentTerminalMirrorSegment => segment.kind === 'terminal',
  );
}

export function findAgentTerminalMirrorSegment(
  content: string,
): AgentTerminalMirrorSegment | null {
  const terminals = listAgentTerminalMirrorSegments(content);
  if (!terminals.length) {
    return null;
  }
  return terminals.find((segment) => segment.open) ?? terminals[terminals.length - 1] ?? null;
}

/** Cheap revision token so mirror sync runs when shell output grows mid-transcript. */
export function terminalMirrorSignature(content: string): string {
  return listAgentTerminalMirrorSegments(content)
    .map((segment) => `${segment.command}\u001f${segment.open ? 1 : 0}\u001f${segment.output.length}`)
    .join('\u001e');
}

export function buildAgentTerminalMirrorText(segment: AgentTerminalMirrorSegment): string {
  const lines = [`$ ${segment.command}`];
  const output = segment.output.replace(/\r\n/g, '\n').replace(/^\n+|\n+$/g, '');
  if (output) {
    lines.push(output);
  }
  // Cursor CLI only emits shell stdout on tool completion — keep an honest
  // in-flight marker while the open `:::terminal` block has no final output yet.
  if (segment.open && !/(^|\n)running…$/.test(output)) {
    lines.push('running…');
  }
  return `${lines.join('\n')}\n`;
}

/** Scrollback of recent in-thread shells — OTA retries stay visible while the next runs. */
export function buildAgentTerminalMirrorScrollback(
  content: string,
  options?: { maxSegments?: number },
): string | null {
  const maxSegments = options?.maxSegments ?? 8;
  const segments = listAgentTerminalMirrorSegments(content);
  if (!segments.length) {
    return null;
  }
  const slice = segments.slice(-maxSegments);
  const blocks = slice.map((segment) => buildAgentTerminalMirrorText(segment).replace(/\n$/, ''));
  return `${blocks.join('\n\n')}\n`;
}

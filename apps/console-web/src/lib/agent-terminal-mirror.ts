/**
 * Cursor-parity mirror: surface in-thread `:::terminal` shell cards in the
 * bottom vaxon terminal tab when the operator presses Background or a shell
 * tool starts during an agent stream.
 */

import { parseAgentTranscriptBlocks, type AgentTranscriptSegment } from './agent-transcript-blocks';
import { buildAgentTerminalJobView } from './agent-terminal-job-view';

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
  const terminals = listAgentTerminalMirrorSegments(content);
  // Only fingerprint the live/latest cards — full-history maps freeze on long OTA threads.
  const window = terminals.slice(-4);
  return window
    .map((segment) => `${segment.command}\u001f${segment.open ? 1 : 0}\u001f${segment.output.length}`)
    .join('\u001e');
}

export function buildAgentTerminalMirrorText(segment: AgentTerminalMirrorSegment): string {
  const job = buildAgentTerminalJobView({
    command: segment.command,
    output: segment.output,
  });
  const commandLabel = job.commandLabel || segment.command;
  const header =
    job.kind === 'shell'
      ? `$ ${commandLabel}`
      : job.headline
        ? `$ ${commandLabel}\n# ${job.headline}`
        : `$ ${commandLabel}`;
  const lines = [header];
  const output = job.displayOutput.replace(/^\n+|\n+$/g, '');
  if (output) {
    lines.push(output);
  }
  // Cursor CLI only emits shell stdout on tool completion — keep an honest
  // in-flight marker while the open `:::terminal` block is still streaming.
  if (
    segment.open &&
    !/(^|\n)running…$/.test(output) &&
    !/\b(Exporting\.\.\.|Uploading\.\.\.|Published)\b/i.test(output)
  ) {
    lines.push('running…');
  }
  return `${lines.join('\n')}\n`;
}

/** Default window — enough for OTA retries without reprocessing entire agent history. */
export const AGENT_TERMINAL_MIRROR_MAX_SEGMENTS = 6;

/** Scrollback of recent in-thread shells — OTA retries stay visible while the next runs. */
export function buildAgentTerminalMirrorScrollback(
  content: string,
  options?: { maxSegments?: number },
): string | null {
  const segments = listAgentTerminalMirrorSegments(content);
  if (!segments.length) {
    return null;
  }
  const maxSegments =
    options?.maxSegments && options.maxSegments > 0
      ? options.maxSegments
      : AGENT_TERMINAL_MIRROR_MAX_SEGMENTS;
  const visibleSegments = segments.slice(-maxSegments);
  const blocks = visibleSegments.map((segment) =>
    buildAgentTerminalMirrorText(segment).replace(/\n$/, ''),
  );
  return `${blocks.join('\n\n')}\n`;
}

/**
 * Ring-buffer diagnostics for the continuous voice loop.
 * Never stores audio or transcripts — only state transitions and latency.
 */

export type VoiceLoopDiagnosticKind =
  | 'hands_free_decision'
  | 'converse_start'
  | 'converse_progress'
  | 'converse_done'
  | 'converse_timeout'
  | 'converse_error'
  | 'wake_gate'
  | 'followup_open'
  | 'followup_close';

export interface VoiceLoopDiagnosticEvent {
  at: number;
  kind: VoiceLoopDiagnosticKind;
  action?: string;
  reason?: string;
  delayMs?: number;
  failures?: number;
  latencyMs?: number;
  phase?: string;
}

const MAX_EVENTS = 80;
const events: VoiceLoopDiagnosticEvent[] = [];

export function recordVoiceLoopDiagnostic(
  event: Omit<VoiceLoopDiagnosticEvent, 'at'> & { at?: number },
): void {
  events.push({
    at: event.at ?? Date.now(),
    kind: event.kind,
    action: event.action,
    reason: event.reason,
    delayMs: event.delayMs,
    failures: event.failures,
    latencyMs: event.latencyMs,
    phase: event.phase,
  });
  if (events.length > MAX_EVENTS) {
    events.splice(0, events.length - MAX_EVENTS);
  }
}

export function listVoiceLoopDiagnostics(): readonly VoiceLoopDiagnosticEvent[] {
  return events;
}

export function clearVoiceLoopDiagnostics(): void {
  events.length = 0;
}

export function summarizeVoiceLoopDiagnostics(): {
  count: number;
  lastKind: VoiceLoopDiagnosticKind | null;
  timeoutCount: number;
  errorCount: number;
} {
  return {
    count: events.length,
    lastKind: events.length ? (events[events.length - 1]?.kind ?? null) : null,
    timeoutCount: events.filter((item) => item.kind === 'converse_timeout').length,
    errorCount: events.filter((item) => item.kind === 'converse_error').length,
  };
}

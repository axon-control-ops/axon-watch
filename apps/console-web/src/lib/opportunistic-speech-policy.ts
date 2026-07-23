/** Desktop-active opportunistic reminder speech (stage 1). */
import type { SpokenAlertEligibility } from '../contracts/canonical';

export type OpportunisticSpeechCandidate = {
  kind: 'reminder' | 'open_loop' | 'incident' | 'check_in';
  text: string;
  priority?: 'low' | 'normal' | 'high';
  memoryId?: string;
};

export type OpportunisticSpeechPolicyInput = {
  consoleActive: boolean;
  quietHours: boolean;
  interruptionsUsed: number;
  maxInterruptionsPerHour: number;
  candidates: OpportunisticSpeechCandidate[];
};

export function selectOpportunisticSpeech(
  input: OpportunisticSpeechPolicyInput,
): OpportunisticSpeechCandidate | null {
  if (!input.consoleActive || input.quietHours) {
    return null;
  }
  if (input.interruptionsUsed >= input.maxInterruptionsPerHour) {
    return null;
  }
  return input.candidates[0] ?? null;
}

export function opportunisticCandidateToSpokenAlert(
  candidate: OpportunisticSpeechCandidate,
): SpokenAlertEligibility {
  return {
    eligible: true,
    reason: `opportunistic_${candidate.kind}`,
    signal_id: candidate.memoryId || `opportunistic:${candidate.kind}`,
    message: candidate.text,
    explanation: {
      what: candidate.text,
      you_do: 'Acknowledge, snooze, or dismiss the reminder.',
      agent_do: 'Speak once within the interruption budget while the console is active.',
      spoken: candidate.text,
    },
  };
}

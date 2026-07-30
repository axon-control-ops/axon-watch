/** Route left-rail speech-chip replies to VAXON vs the teammate who asked. */

import type { CompanyEmployeeRecord } from '../contracts/canonical';
import type { KairoVoiceSpeakerKind } from './kairo-voice-utterance';
import {
  isAffirmativeOperatorReply,
  spokenLineAsksForRetry,
  vaxonLineAsksForReply,
} from './vaxon-reply-prompt';

export type SidebarSpeechReplyTarget =
  | { kind: 'vaxon' }
  | { kind: 'employee'; employee: CompanyEmployeeRecord; retry: boolean };

export function resolveSidebarSpeechReplyTarget(input: {
  line: string;
  speakerKind: KairoVoiceSpeakerKind | null | undefined;
  speakerId: string | null | undefined;
  speakerName: string | null | undefined;
  vaxonName: string;
  employees: CompanyEmployeeRecord[];
  message?: string | null;
}): SidebarSpeechReplyTarget {
  const speakerKind = input.speakerKind ?? null;
  const isEmployeeSurface =
    speakerKind === 'employee' ||
    Boolean(
      input.speakerName?.trim() &&
        input.speakerName.trim().toLowerCase() !== input.vaxonName.trim().toLowerCase() &&
        input.speakerId?.trim() &&
        input.speakerId.trim().toLowerCase() !== 'vaxon',
    );

  if (!isEmployeeSurface) {
    return { kind: 'vaxon' };
  }

  const employee =
    input.employees.find((row) => row.employee_id === input.speakerId?.trim()) ||
    input.employees.find(
      (row) => row.name.trim().toLowerCase() === input.speakerName?.trim().toLowerCase(),
    );

  if (!employee) {
    return { kind: 'vaxon' };
  }

  const message = String(input.message ?? '').trim();
  const retry =
    spokenLineAsksForRetry(input.line) &&
    (!message || isAffirmativeOperatorReply(message) || spokenLineAsksForRetry(message));

  return { kind: 'employee', employee, retry };
}

export function sidebarSpeechShouldOfferReply(input: {
  line: string;
  speakerKind: KairoVoiceSpeakerKind | null | undefined;
  stickyNeedsDecision: boolean;
  pendingVaxonDecision: boolean;
  followupActive: boolean;
}): boolean {
  const line = input.line.trim();
  if (!line) {
    return false;
  }
  if (input.speakerKind === 'employee') {
    return vaxonLineAsksForReply(line);
  }
  if (vaxonLineAsksForReply(line)) {
    return true;
  }
  return input.stickyNeedsDecision || input.pendingVaxonDecision || input.followupActive;
}

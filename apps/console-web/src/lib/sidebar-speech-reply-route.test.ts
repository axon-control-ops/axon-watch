import { describe, expect, it } from 'vitest';

import type { CompanyEmployeeRecord } from '../contracts/canonical';
import {
  resolveSidebarSpeechReplyTarget,
  sidebarSpeechShouldOfferReply,
} from './sidebar-speech-reply-route';

const dana = {
  employee_id: 'emp_dana',
  name: 'Dana',
  role: 'lead',
  role_label: 'Lead',
  status: 'idle',
  enabled: true,
} as CompanyEmployeeRecord;

describe('resolveSidebarSpeechReplyTarget', () => {
  it('routes Try again on Dana speech to the employee retry path', () => {
    const target = resolveSidebarSpeechReplyTarget({
      line: 'I can try again, or explain what happened — your call.',
      speakerKind: 'employee',
      speakerId: 'emp_dana',
      speakerName: 'Dana',
      vaxonName: 'VAXON',
      employees: [dana],
      message: 'Try again',
    });
    expect(target).toEqual({ kind: 'employee', employee: dana, retry: true });
  });

  it('keeps VAXON as the reply target for operator briefing lines', () => {
    const target = resolveSidebarSpeechReplyTarget({
      line: 'Shall I open Attention?',
      speakerKind: 'vaxon',
      speakerId: 'vaxon',
      speakerName: 'VAXON',
      vaxonName: 'VAXON',
      employees: [dana],
      message: 'yes',
    });
    expect(target).toEqual({ kind: 'vaxon' });
  });
});

describe('sidebarSpeechShouldOfferReply', () => {
  it('offers a reply when an employee asks to try again', () => {
    expect(
      sidebarSpeechShouldOfferReply({
        line: 'I can try again, or explain what happened — your call.',
        speakerKind: 'employee',
        stickyNeedsDecision: false,
        pendingVaxonDecision: true,
        followupActive: true,
      }),
    ).toBe(true);
  });

  it('does not offer a reply for plain employee narration', () => {
    expect(
      sidebarSpeechShouldOfferReply({
        line: 'Quiet for now on DashPro priorities.',
        speakerKind: 'employee',
        stickyNeedsDecision: false,
        pendingVaxonDecision: true,
        followupActive: true,
      }),
    ).toBe(false);
  });
});

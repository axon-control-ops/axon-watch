import { computed, ref } from 'vue';

import type { CompanyEmployeeRecord } from '../../contracts/canonical';
import { clearBriefingSurfaceOffer } from '../kairo-conversation/conversation-briefing-surface';
import { clearQueuedSpokenAlerts } from '../../lib/spoken-alert-delivery';
import type { ReportTheaterPayload, ReportTheaterSections } from './report-theater-model';
import {
  buildReportTheaterStages,
  normalizeReportTheaterSections,
  parseReportSectionsFromReply,
} from './report-theater-model';
import {
  toVaxonDirectiveLine,
  type ReportTheaterDirective,
} from './report-theater-directives';

const open = ref(false);
const sections = ref<ReportTheaterSections>(normalizeReportTheaterSections(null));
const fingerprint = ref<string | null>(null);
const replyText = ref('');
const stageIndex = ref(0);
const showNextSteps = ref(false);
const executing = ref(false);
const speakerName = ref<string | null>(null);
const directives = ref<ReportTheaterDirective[]>([]);
/** Frozen at open so attendee chips stay aligned with spoken sections. */
const attendeesRoster = ref<CompanyEmployeeRecord[]>([]);
/** Bumps when a new theater session starts so in-flight narration can cancel. */
const sessionToken = ref(0);

export const reportTheaterOpen = computed(() => open.value);
export const reportTheaterSections = computed(() => sections.value);
export const reportTheaterFingerprint = computed(() => fingerprint.value);
export const reportTheaterReply = computed(() => replyText.value);
export const reportTheaterStageIndex = computed(() => stageIndex.value);
export const reportTheaterShowNextSteps = computed(() => showNextSteps.value);
export const reportTheaterExecuting = computed(() => executing.value);
export const reportTheaterSpeakerName = computed(() => speakerName.value);
export const reportTheaterDirectives = computed(() => directives.value);
export const reportTheaterAttendeesRoster = computed(() => attendeesRoster.value);
export const reportTheaterStages = computed(() => buildReportTheaterStages(sections.value));
export const reportTheaterSessionToken = computed(() => sessionToken.value);

export function openReportTheater(payload: ReportTheaterPayload): void {
  const fromApi = normalizeReportTheaterSections(payload.sections);
  const hasStructured =
    fromApi.attention.length > 0 ||
    fromApi.work_in_flight.length > 0 ||
    fromApi.lead_rollups.length > 0 ||
    fromApi.fleet.length > 0 ||
    Boolean(fromApi.next_move);
  const normalized = hasStructured
    ? fromApi
    : parseReportSectionsFromReply(payload.reply || payload.spokenReply || '');
  sections.value = {
    ...normalized,
    next_move: toVaxonDirectiveLine(normalized.next_move).replace(/\.+$/, ''),
  };
  fingerprint.value = payload.fingerprint?.trim() || null;
  replyText.value = String(payload.reply || payload.spokenReply || '').trim();
  attendeesRoster.value = Array.isArray(payload.employees)
    ? payload.employees.map((row) => ({ ...row }))
    : [];
  // -1 = intro/preamble — do not show Attention while "Here's the stand-up" plays.
  stageIndex.value = -1;
  showNextSteps.value = false;
  executing.value = false;
  speakerName.value = 'VAXON';
  sessionToken.value += 1;
  open.value = true;
  clearBriefingSurfaceOffer();
  clearQueuedSpokenAlerts();
}

export function setReportTheaterStageIndex(index: number): void {
  const max = Math.max(0, reportTheaterStages.value.length - 1);
  stageIndex.value = Math.max(0, Math.min(max, Math.floor(index)));
}

export function advanceReportTheaterStage(): void {
  const max = reportTheaterStages.value.length - 1;
  if (stageIndex.value < max) {
    stageIndex.value += 1;
    return;
  }
  showNextSteps.value = true;
}

export function revealReportTheaterNextSteps(): void {
  stageIndex.value = Math.max(stageIndex.value, reportTheaterStages.value.length - 1);
  showNextSteps.value = true;
}

export function setReportTheaterExecuting(active: boolean): void {
  executing.value = Boolean(active);
}

export function setReportTheaterSpeakerName(name: string | null): void {
  speakerName.value = name?.trim() || null;
}

export function setReportTheaterDirectives(items: ReportTheaterDirective[]): void {
  directives.value = [...items];
}

export function closeReportTheater(): void {
  open.value = false;
  showNextSteps.value = false;
  executing.value = false;
  stageIndex.value = 0;
  fingerprint.value = null;
  replyText.value = '';
  speakerName.value = null;
  directives.value = [];
  attendeesRoster.value = [];
  sections.value = normalizeReportTheaterSections(null);
}

export function resetReportTheaterStateForTests(): void {
  closeReportTheater();
}

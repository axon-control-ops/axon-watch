import type { KairoNarrationLevel } from '../contracts/canonical';

import type { IdePresenceProfile } from './ide-presence-profile';

export function effectiveKairoNarration(input: {
  settingsNarration: KairoNarrationLevel;
  layoutMode: 'operator' | 'ide';
  idePresenceProfile: IdePresenceProfile;
}): KairoNarrationLevel {
  if (input.layoutMode === 'ide' && input.idePresenceProfile === 'quiet') {
    if (input.settingsNarration === 'conversational') {
      return 'conversational';
    }
    return 'off';
  }
  return input.settingsNarration;
}

export function shouldNarrateAgentEvent(input: {
  eventKey: string;
  narration: KairoNarrationLevel;
}): boolean {
  if (input.narration === 'off') {
    return false;
  }
  // Bookends only for both minimal and conversational. Tool/edit milestones stay
  // silent until opt-in tool narration ships. Live thinking uses
  // shouldSpeakLiveThinkingBlock instead of this gate.
  return (
    input.eventKey === 'start' ||
    input.eventKey === 'done' ||
    input.eventKey === 'failed' ||
    input.eventKey.startsWith('alert')
  );
}

export function shouldSpeakLiveThinkingBlock(input: {
  narration: KairoNarrationLevel;
  spokenBlock: string;
}): boolean {
  if (input.narration === 'off' || !input.spokenBlock.trim()) {
    return false;
  }
  // Speak the first complete thinking sentence as the run-start intent.
  return /[.!?]$/.test(input.spokenBlock.trim());
}

/** Progress milestones (run/research/verify) — not the same as agent bookends. */
const PROGRESS_MINIMAL_EVENTS = new Set([
  'approval_required',
  'stream_error',
  'unverified_complete',
]);

const PROGRESS_CONVERSATIONAL_SKIP = new Set([
  'run_started',
  'research_started',
  'research_complete',
  'verified_complete',
]);

export function shouldNarrateProgressMilestone(input: {
  eventType: string;
  narration: KairoNarrationLevel;
}): boolean {
  if (input.narration === 'off') {
    return false;
  }
  if (input.narration === 'minimal') {
    return PROGRESS_MINIMAL_EVENTS.has(input.eventType);
  }
  // Conversational: live thinking covers run progress; skip canned status lines.
  return !PROGRESS_CONVERSATIONAL_SKIP.has(input.eventType);
}

export function mapMilestoneToSpeakEvent(milestoneKey: string): string {
  if (milestoneKey === 'start') {
    return 'agent_start';
  }
  if (milestoneKey.startsWith('thinking')) {
    return 'thinking';
  }
  if (milestoneKey.startsWith('tool:')) {
    return 'tool';
  }
  if (milestoneKey.startsWith('edit:')) {
    return 'edit';
  }
  if (milestoneKey === 'done') {
    return 'done';
  }
  if (milestoneKey === 'failed') {
    return 'failed';
  }
  return 'thinking';
}

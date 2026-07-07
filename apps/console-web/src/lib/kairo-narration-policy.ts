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
  // Bookends only — avoid narrating every tool/edit/thinking milestone.
  const isBookend =
    input.eventKey === 'start' || input.eventKey === 'done' || input.eventKey.startsWith('alert');
  if (input.narration === 'conversational') {
    return isBookend;
  }
  return isBookend;
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
  return 'thinking';
}

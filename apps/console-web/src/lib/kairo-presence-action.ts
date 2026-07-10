import type { KairoPresenceState } from './kairo-presence';

export type KairoPresenceClickTarget =
  | 'resume'
  | 'pause'
  | 'interrupt'
  | 'attention'
  | 'briefing';

export function resolveKairoPresenceClickTarget(input: {
  paused: boolean;
  voiceBusy: boolean;
  layoutMode: 'ide' | 'operator' | string;
  state: KairoPresenceState;
}): KairoPresenceClickTarget {
  if (input.paused) {
    return 'resume';
  }

  if (input.layoutMode === 'ide') {
    if (input.voiceBusy) {
      return 'pause';
    }
    return input.state === 'alerting' ? 'attention' : 'briefing';
  }

  if (input.voiceBusy) {
    return 'interrupt';
  }

  return input.state === 'alerting' ? 'attention' : 'briefing';
}

import { reactive } from 'vue';

// Local, per-browser "read" tracking for detected emails -- deliberately NOT
// backed by the fleet signal system. Calling acknowledgeInboxSignals to mean
// "I looked at this" resolves the signal at its source with no undo, which
// is meant for "this is handled" (a real operator decision), not a side
// effect of opening an email. A single reactive module (not per-component
// state) so the Email tab's list and the Mission Control tab badge -- two
// separate component instances -- agree on what's read without a re-fetch.
const READ_SIGNAL_IDS_KEY = 'axon-x-read-email-signal-ids-v1';

function loadReadSignalIds(): Set<string> {
  if (typeof window === 'undefined') {
    return new Set();
  }
  try {
    const raw = window.localStorage.getItem(READ_SIGNAL_IDS_KEY);
    const parsed = raw ? JSON.parse(raw) : [];
    return new Set(Array.isArray(parsed) ? parsed.map(String) : []);
  } catch {
    return new Set();
  }
}

const state = reactive({ readSignalIds: loadReadSignalIds() });

export function isEmailSignalRead(signalId: string): boolean {
  return state.readSignalIds.has(signalId);
}

export function markEmailSignalRead(signalId: string): void {
  if (state.readSignalIds.has(signalId)) {
    return;
  }
  state.readSignalIds.add(signalId);
  if (typeof window !== 'undefined') {
    window.localStorage.setItem(
      READ_SIGNAL_IDS_KEY,
      JSON.stringify([...state.readSignalIds]),
    );
  }
}

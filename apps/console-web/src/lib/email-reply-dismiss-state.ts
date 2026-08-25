import { reactive } from 'vue';

// Local, per-browser "I don't want this suggested reply" state -- purely a
// display preference. Never touches the underlying signal (that stays open
// until the operator actually handles the email); dismissing only hides the
// reply-draft card from the Live Ops rail so it can be reversed by simply
// reloading, same rationale as email-read-state.ts.
const DISMISSED_KEY = 'axon-x-dismissed-reply-signal-ids-v1';

function loadDismissedSignalIds(): Set<string> {
  if (typeof window === 'undefined') {
    return new Set();
  }
  try {
    const raw = window.localStorage.getItem(DISMISSED_KEY);
    const parsed = raw ? JSON.parse(raw) : [];
    return new Set(Array.isArray(parsed) ? parsed.map(String) : []);
  } catch {
    return new Set();
  }
}

const state = reactive({ dismissedSignalIds: loadDismissedSignalIds() });

export function isReplySuggestionDismissed(signalId: string): boolean {
  return state.dismissedSignalIds.has(signalId);
}

export function dismissReplySuggestion(signalId: string): void {
  if (state.dismissedSignalIds.has(signalId)) {
    return;
  }
  state.dismissedSignalIds.add(signalId);
  if (typeof window !== 'undefined') {
    window.localStorage.setItem(
      DISMISSED_KEY,
      JSON.stringify([...state.dismissedSignalIds]),
    );
  }
}

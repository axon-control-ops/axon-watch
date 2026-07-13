export type BriefingVoiceTranscriptEntry = {
  id: string;
  createdAt: string;
  message: string;
  workspaceId: string | null;
};

const BRIEFING_VOICE_TRANSCRIPT_KEY = 'axon-x:briefing-voice-transcript';
const MAX_BRIEFING_VOICE_TRANSCRIPT = 6;

function storage(): Storage | null {
  return typeof sessionStorage === 'undefined' ? null : sessionStorage;
}

function normalizeEntry(raw: unknown): BriefingVoiceTranscriptEntry | null {
  if (!raw || typeof raw !== 'object') {
    return null;
  }
  const entry = raw as Record<string, unknown>;
  const id = String(entry.id ?? '').trim();
  const createdAt = String(entry.createdAt ?? '').trim();
  const message = String(entry.message ?? '').trim();
  const workspaceIdRaw = entry.workspaceId;
  const workspaceId =
    typeof workspaceIdRaw === 'string' && workspaceIdRaw.trim()
      ? workspaceIdRaw.trim()
      : null;
  if (!id || !createdAt || !message) {
    return null;
  }
  return { id, createdAt, message, workspaceId };
}

export function readBriefingVoiceTranscript(): BriefingVoiceTranscriptEntry[] {
  const backing = storage();
  if (!backing) {
    return [];
  }
  try {
    const raw = backing.getItem(BRIEFING_VOICE_TRANSCRIPT_KEY);
    if (!raw) {
      return [];
    }
    const parsed = JSON.parse(raw) as unknown[];
    if (!Array.isArray(parsed)) {
      return [];
    }
    return parsed
      .map(normalizeEntry)
      .filter((entry): entry is BriefingVoiceTranscriptEntry => entry !== null)
      .slice(0, MAX_BRIEFING_VOICE_TRANSCRIPT);
  } catch {
    return [];
  }
}

export function persistBriefingVoiceTranscript(
  entries: BriefingVoiceTranscriptEntry[],
): BriefingVoiceTranscriptEntry[] {
  const normalized = entries
    .map(normalizeEntry)
    .filter((entry): entry is BriefingVoiceTranscriptEntry => entry !== null)
    .slice(0, MAX_BRIEFING_VOICE_TRANSCRIPT);
  const backing = storage();
  if (backing) {
    try {
      backing.setItem(BRIEFING_VOICE_TRANSCRIPT_KEY, JSON.stringify(normalized));
    } catch {
      // Ignore sessionStorage write failures and keep in-memory state.
    }
  }
  return normalized;
}

export function appendBriefingVoiceTranscriptEntry(input: {
  message: string;
  workspaceId?: string | null;
}): BriefingVoiceTranscriptEntry[] {
  const message = String(input.message ?? '').trim();
  if (!message) {
    return readBriefingVoiceTranscript();
  }
  const next: BriefingVoiceTranscriptEntry = {
    id: `briefing-voice-${Date.now()}`,
    createdAt: new Date().toISOString(),
    message,
    workspaceId: input.workspaceId?.trim() || null,
  };
  return persistBriefingVoiceTranscript([next, ...readBriefingVoiceTranscript()]);
}

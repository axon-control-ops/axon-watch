export type KairoVoiceLogEntry = {
  entry_id: string;
  created_at: string;
  session_id: string;
  workspace_id: string | null;
  raw_content: string;
  normalized_content: string;
  reply: string;
  turn_kind: string;
  source: string;
  stt_note: string | null;
};

export async function fetchKairoVoiceLog(limit = 8): Promise<KairoVoiceLogEntry[]> {
  const baseUrl = import.meta.env.VITE_CONTROL_PLANE_BASE_URL ?? '';
  const url = baseUrl
    ? `${baseUrl}/api/kairo/voice-log?limit=${limit}`
    : `/api/kairo/voice-log?limit=${limit}`;
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`voice log request failed with status ${response.status}`);
  }
  const payload = (await response.json()) as { entries?: KairoVoiceLogEntry[] };
  return payload.entries ?? [];
}

export function logKairoVoice(event: string, detail: Record<string, unknown> = {}): void {
  if (!import.meta.env.DEV) {
    return;
  }
  console.debug('[kairo-voice]', event, detail);
}

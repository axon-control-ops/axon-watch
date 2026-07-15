import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

import { buildKairoSpeechSessionId } from './kairo-speech-session';

const testDir = dirname(fileURLToPath(import.meta.url));
const srcRoot = resolve(testDir, '..');

function readSource(relativePath: string): string {
  return readFileSync(resolve(srcRoot, relativePath), 'utf8');
}

describe('buildKairoSpeechSessionId', () => {
  it('binds session id to workspace and thread', () => {
    expect(buildKairoSpeechSessionId('workspace_dashpro', 'thread_abc')).toBe(
      'kairo:workspace_dashpro:thread_abc',
    );
  });

  it('falls back to default bucket when thread is missing', () => {
    expect(buildKairoSpeechSessionId('workspace_dashpro', null)).toBe(
      'kairo:workspace_dashpro:default',
    );
  });
});

describe('M1 session identity contract', () => {
  it('routes converse and speak through the same shell session id', () => {
    const shellSource = readSource('stores/shell.ts');
    const voiceSliceSource = readSource('stores/shell/slices/create-kairo-voice-slice.ts');
    const converseSource = readSource('features/kairo-conversation/use-kairo-conversation.ts');
    const appVoiceSource = readSource('features/kairo-conversation/use-kairo-app-voice.ts');

    expect(voiceSliceSource).toMatch(/function kairoSpeechSessionId\(\)/);
    expect(voiceSliceSource).toMatch(/buildKairoSpeechSessionId/);
    expect(shellSource).not.toMatch(/sessionStorage.*kairo-speech-session/);
    expect(converseSource).toMatch(/session_id:\s*kairoSpeechSessionId\(\)/);
    expect(converseSource).toMatch(/return shell\.kairoSpeechSessionId\(\)/);
    expect(appVoiceSource).toMatch(/session_id:\s*shell\.kairoSpeechSessionId\(\)/);
    expect(voiceSliceSource).toMatch(/session_id:\s*kairoSpeechSessionId\(\)/);
  });

  it('routes agent milestone speak through the same session id supplier', () => {
    const shellSource = readSource('stores/shell.ts');
    expect(shellSource).toMatch(/sessionId:\s*kairoSpeechSessionId/);
  });
});

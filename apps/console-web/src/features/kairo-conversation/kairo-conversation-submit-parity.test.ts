import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

const testDir = dirname(fileURLToPath(import.meta.url));

function readSibling(name: string): string {
  return readFileSync(resolve(testDir, name), 'utf8');
}

describe('KAIRO typed and voice submission parity', () => {
  it('registers the same submitTurn implementation for app voice', () => {
    const appVoice = readSibling('use-kairo-app-voice.ts');

    expect(appVoice).toMatch(/const \{ submitTurn \} = useKairoConversation\(\)/);
    expect(appVoice).toMatch(/registerKairoConversationSubmit\(submitTurn\)/);
    expect(appVoice).not.toMatch(/postKairoConverse/);
    expect(appVoice).not.toMatch(/dispatchKairoConverseOutcome/);
  });

  it('keeps request context, receipts, dispatch, and errors in submitTurn', () => {
    const conversation = readSibling('use-kairo-conversation.ts');

    expect(conversation).toMatch(/context_workspace_id:/);
    expect(conversation).toMatch(/context_signal_id:/);
    expect(conversation).toMatch(/context_node_id:/);
    expect(conversation).toMatch(/await dispatchKairoConverseOutcome/);
    expect(conversation).toMatch(/kairoConversationError\.value/);
  });
});

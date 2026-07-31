import fs from 'node:fs';
import path from 'node:path';
import { describe, expect, it } from 'vitest';

describe('agent dock kairo attachment bridge', () => {
  it('bridges composerImages into submitKairoTurn so dock attaches send', () => {
    const source = fs.readFileSync(
      path.resolve(__dirname, './use-composer-actions.ts'),
      'utf8',
    );
    expect(source).toContain('dockAttachments');
    expect(source).toContain('await submitKairoTurn(draft, { dockAttachments })');
    expect(source).toContain('if (sent !== false)');
  });

  it('accepts dockAttachments on the VAXON submitTurn path', () => {
    const source = fs.readFileSync(
      path.resolve(
        __dirname,
        '../../features/kairo-conversation/use-kairo-conversation.ts',
      ),
      'utf8',
    );
    expect(source).toContain('dockAttachments?: ComposerClipboardImage[]');
    expect(source).toContain('...(options?.dockAttachments ?? [])');
  });
});

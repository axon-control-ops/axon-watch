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

  it('clears the origin draft before dispatch and restores it only on failure', () => {
    const source = fs.readFileSync(
      path.resolve(__dirname, './use-composer-actions.ts'),
      'utf8',
    );
    const routedPrompt = source.indexOf('const routedPrompt =');
    const clearDraft = source.indexOf("shell.ideComposerDraft = '';", routedPrompt);
    const persistClear = source.indexOf("persistIdeComposerDraft(workspaceId, '', originThreadId);", routedPrompt);
    const submit = source.indexOf('await shell.submitIdeComposer(modeForSubmit', routedPrompt);
    const restore = source.indexOf('shell.ideComposerDraft = submitDraft;', submit);

    expect(clearDraft).toBeGreaterThan(routedPrompt);
    expect(persistClear).toBeGreaterThan(clearDraft);
    expect(submit).toBeGreaterThan(persistClear);
    expect(restore).toBeGreaterThan(submit);
  });

  it('synchronously clears thread storage on dispatch and queue success', () => {
    const source = fs.readFileSync(
      path.resolve(__dirname, '../../stores/shell.ts'),
      'utf8',
    );

    expect(source).toContain("persistIdeComposerDraft(workspaceId, '', response.thread_id);");
    expect(source).toContain(
      "activeIdeThreadId.value || null,\n      );\n      commandMutationError.value = null;",
    );
  });
});

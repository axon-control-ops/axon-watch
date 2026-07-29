import { beforeEach, describe, expect, it, vi } from 'vitest';

const focusAgentDockComposerInput = vi.fn();
const requestIdeComposerMode = vi.fn();
const restoreComposerDraft = vi.fn();
const submitIdeComposer = vi.fn(async () => undefined);

let draftValue = '';
let commandMutationState = 'idle';
let agentStreamActive = false;

vi.mock('./agent-dock-composer-focus', () => ({
  focusAgentDockComposerInput: (...args: unknown[]) => focusAgentDockComposerInput(...args),
}));

vi.mock('./ide-composer-restore-request', () => ({
  requestIdeComposerMode: (...args: unknown[]) => requestIdeComposerMode(...args),
}));

vi.mock('../stores/shell', () => ({
  useShellStore: () => ({
    get commandMutationState() {
      return commandMutationState;
    },
    get agentStreamActive() {
      return agentStreamActive;
    },
    get ideComposerDraft() {
      return draftValue;
    },
    set ideComposerDraft(value: string) {
      draftValue = value;
    },
    restoreComposerDraft: (...args: unknown[]) => restoreComposerDraft(...args),
    submitIdeComposer: (...args: unknown[]) => submitIdeComposer(...args),
  }),
}));

describe('operator-message-composer-actions', () => {
  beforeEach(() => {
    draftValue = 'prior draft';
    commandMutationState = 'idle';
    agentStreamActive = false;
    focusAgentDockComposerInput.mockReset();
    requestIdeComposerMode.mockReset();
    restoreComposerDraft.mockReset();
    submitIdeComposer.mockReset();
    submitIdeComposer.mockImplementation(async () => {
      draftValue = '';
    });
    vi.resetModules();
  });

  it('loads command edits into the composer', async () => {
    const { restoreOperatorTextToComposer } = await import('./operator-message-composer-actions');
    restoreOperatorTextToComposer('fix me');
    expect(requestIdeComposerMode).toHaveBeenCalledWith('agent');
    expect(restoreComposerDraft).toHaveBeenCalledWith('fix me');
    expect(focusAgentDockComposerInput).toHaveBeenCalledOnce();
  });

  it('submits inline YOU edits without leaving text in the composer', async () => {
    const { submitOperatorPromptInline } = await import('./operator-message-composer-actions');
    const ok = await submitOperatorPromptInline('Ok start with three class moves');
    expect(ok).toBe(true);
    expect(requestIdeComposerMode).toHaveBeenCalledWith('agent');
    expect(submitIdeComposer).toHaveBeenCalledWith('agent');
    expect(draftValue).toBe('');
  });

  it('restores the prior composer draft when inline submit does not clear', async () => {
    submitIdeComposer.mockImplementation(async () => undefined);
    const { submitOperatorPromptInline } = await import('./operator-message-composer-actions');
    const ok = await submitOperatorPromptInline('still here');
    expect(ok).toBe(false);
    expect(draftValue).toBe('prior draft');
  });

  it('resolves regenerate prompt from the preceding YOU turn', async () => {
    const { agentReplyRegeneratePrompt } = await import('./operator-message-composer-actions');
    expect(agentReplyRegeneratePrompt('  option 2  ')).toBe('option 2');
    expect(agentReplyRegeneratePrompt('')).toBeNull();
    expect(agentReplyRegeneratePrompt(null)).toBeNull();
  });

  it('regenerates an agent reply by resubmitting the preceding YOU prompt', async () => {
    const { regenerateAgentReplyFromPrompt } = await import('./operator-message-composer-actions');
    const ok = await regenerateAgentReplyFromPrompt('I think option 2 is the best');
    expect(ok).toBe(true);
    expect(submitIdeComposer).toHaveBeenCalledWith('agent');
    expect(draftValue).toBe('');
  });

  it('skips regenerate when there is no preceding YOU prompt', async () => {
    const { regenerateAgentReplyFromPrompt } = await import('./operator-message-composer-actions');
    const ok = await regenerateAgentReplyFromPrompt('   ');
    expect(ok).toBe(false);
    expect(submitIdeComposer).not.toHaveBeenCalled();
  });
});

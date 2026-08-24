import { markQuestionAnswered } from './answered-agent-questions';
import { readWorkspaceComposerMode } from './composer-mode-prefs';
import { formatQuestionAnswer, type AgentQuestionOption } from './agent-question-view';
import { requestIdeComposerMode } from './ide-composer-restore-request';
import type { IdeComposerMode } from './ide-composer-queue';

export type SubmitQuestionAnswerShell = {
  openIdeComposerWithDraft: (content: string) => void;
  submitIdeComposer: (mode: IdeComposerMode) => Promise<boolean | 'queued' | void>;
  activeIdeThreadId?: string | null;
};

/** 'dispatched' = the agent actually received it; 'queued' = held behind the
 * current stream and not yet delivered — callers must not treat this as answered. */
export type SubmitQuestionAnswerResult = 'dispatched' | 'queued';

function resolveSubmitMode(
  workspaceId: string | null | undefined,
  threadId?: string | null,
): IdeComposerMode {
  const stored = readWorkspaceComposerMode(workspaceId, sessionStorage, threadId);
  if (!stored || stored === 'kairo') {
    return stored === 'kairo' ? 'ask' : 'agent';
  }
  return stored;
}

export async function submitQuestionAnswer(
  shell: SubmitQuestionAnswerShell,
  input: {
    workspaceId: string | null | undefined;
    option: AgentQuestionOption;
    prompt?: string;
    messageId?: string;
    customText?: string;
  },
): Promise<SubmitQuestionAnswerResult> {
  const answer = formatQuestionAnswer(input.option, input.prompt, input.customText).trim();
  if (!answer) {
    return 'dispatched';
  }
  const mode = resolveSubmitMode(input.workspaceId, shell.activeIdeThreadId);
  requestIdeComposerMode(mode);
  shell.openIdeComposerWithDraft(answer);
  const submitted = await shell.submitIdeComposer(mode);
  if (submitted === false) {
    throw new Error('Unable to send this choice. Your selection is still available.');
  }
  const dispatched = submitted !== 'queued';
  // Only mark the ask "answered" once the agent has actually received it —
  // a queued answer is still sitting in the composer queue, not delivered.
  if (dispatched && input.messageId && input.prompt) {
    markQuestionAnswered(input.messageId, input.prompt);
  }
  return dispatched ? 'dispatched' : 'queued';
}

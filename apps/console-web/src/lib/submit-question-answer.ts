import { markQuestionAnswered } from './answered-agent-questions';
import { readWorkspaceComposerMode } from './composer-mode-prefs';
import { formatQuestionAnswer, type AgentQuestionOption } from './agent-question-view';
import { requestIdeComposerMode } from './ide-composer-restore-request';
import type { IdeComposerMode } from './ide-composer-queue';

export type SubmitQuestionAnswerShell = {
  openIdeComposerWithDraft: (content: string) => void;
  submitIdeComposer: (mode: IdeComposerMode) => Promise<void>;
  activeIdeThreadId?: string | null;
};

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
): Promise<void> {
  const answer = formatQuestionAnswer(input.option, input.prompt, input.customText).trim();
  if (!answer) {
    return;
  }
  const mode = resolveSubmitMode(input.workspaceId, shell.activeIdeThreadId);
  requestIdeComposerMode(mode);
  if (input.messageId && input.prompt) {
    markQuestionAnswered(input.messageId, input.prompt);
  }
  shell.openIdeComposerWithDraft(answer);
  await shell.submitIdeComposer(mode);
}

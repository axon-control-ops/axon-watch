/**
 * Context-aware copy for the composer's "awaiting approval" banner.
 *
 * The banner used to show one static line — "Full Access is paused — tap
 * Approve to let tools continue, or Reject to stop." — for every reason a run
 * can sit in `awaiting_approval`. That phase now also covers a worker asking
 * the operator a question it cannot answer itself (`block_run_on_operator_ask`
 * on the backend), and the generic banner is actively wrong there:
 *
 * - "Approve" just resumes the run with no new information, so the worker
 *   either re-asks the same question or proceeds having learned nothing.
 * - "Reject" cancels the *entire task*, not "no" to the specific question —
 *   there is no path back to redirecting the work.
 *
 * The real way to answer an ask-block is the queued "Selected option N: ..."
 * composer message the decision card already writes. This helper detects that
 * case from `current_step` (set verbatim by `block_run_on_operator_ask`) and
 * points the operator at the actual answer path instead of the generic pair
 * of buttons.
 */

const ASK_BLOCK_PREFIX = 'Blocked on operator decision:';

export type ApprovalBannerView = {
  isAskBlock: boolean;
  /** The worker's actual question, when known. */
  question: string;
  bannerCopy: string;
  approveLabel: string;
  rejectLabel: string;
  /** Shown near Reject only for an ask-block, where it cancels the whole task. */
  rejectWarning: string;
};

export function describeApprovalBanner(currentStep: string | null | undefined): ApprovalBannerView {
  const step = String(currentStep || '').trim();
  if (step.startsWith(ASK_BLOCK_PREFIX)) {
    const question = step.slice(ASK_BLOCK_PREFIX.length).trim();
    return {
      isAskBlock: true,
      question,
      bannerCopy: question
        ? `Waiting on your answer: ${question}`
        : 'Waiting on your answer to continue.',
      approveLabel: 'Resume without answering',
      rejectLabel: 'Cancel this task',
      rejectWarning: 'This cancels the whole task, not just this question.',
    };
  }
  return {
    isAskBlock: false,
    question: '',
    bannerCopy: 'Full Access is paused — tap Approve to let tools continue, or Reject to stop.',
    approveLabel: 'Approve',
    rejectLabel: 'Reject',
    rejectWarning: '',
  };
}

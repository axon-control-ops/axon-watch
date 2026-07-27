/** Central operator-facing copy for failure banner / recovery actions. */

export const OPERATOR_FAILURE_RETRY_LABEL = 'Try again';
export const OPERATOR_FAILURE_CONTINUE_LABEL = 'Continue';
export const OPERATOR_FAILURE_STATUS_LABEL = 'last job failed';

export function operatorFailureRetryLabel(interrupted: boolean): string {
  return interrupted ? OPERATOR_FAILURE_CONTINUE_LABEL : OPERATOR_FAILURE_RETRY_LABEL;
}

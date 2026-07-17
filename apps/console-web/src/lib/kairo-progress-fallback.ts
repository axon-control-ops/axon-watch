import { toolMilestoneSpeakLine } from './kairo-tool-milestone';

export interface ProgressFallbackInput {
  eventType: string;
  context?: Record<string, unknown>;
}

function operatorPrompt(context?: Record<string, unknown>): string {
  return String(context?.operator_prompt ?? '')
    .replace(/\s+/g, ' ')
    .trim();
}

function runStartedLine(prompt: string): string {
  if (!prompt) {
    return 'Run started.';
  }
  if (/^(?:hi|hello|hey|good morning|good afternoon|good evening)\b/i.test(prompt)) {
    return '';
  }
  // Agent-run start intent comes from the first thinking sentence, not a canned line.
  return '';
}

export function progressFallbackLine(input: ProgressFallbackInput): string {
  const prompt = operatorPrompt(input.context);
  const query = String(input.context?.research_query ?? '')
    .replace(/\s+/g, ' ')
    .trim();
  const warning = String(input.context?.warning_summary ?? '')
    .replace(/\s+/g, ' ')
    .trim();
  const failure = String(input.context?.failure_summary ?? '')
    .replace(/\s+/g, ' ')
    .trim();

  switch (input.eventType) {
    case 'run_started':
      return runStartedLine(prompt);
    case 'research_started':
      return query
        ? `I am checking ${query} against the available evidence now.`
        : 'I am checking the available evidence now.';
    case 'research_complete':
      return query
        ? `I have finished checking ${query}.`
        : 'I have finished checking the evidence.';
    case 'approval_required':
      return 'I need your approval before I can continue.';
    case 'verified_complete':
      return 'I have verified the result and it is ready for review.';
    case 'unverified_complete':
      return warning
        ? `I have a result, but it still needs verification: ${warning}`
        : 'I have a result, but it still needs verification before I call it done.';
    case 'stream_error':
      return failure ? `The run hit an error: ${failure}` : 'The run hit an error before completion.';
    case 'done':
      return taskSummaryFromContext(input.context) || 'Done.';
    case 'agent_failed':
      return failure
        ? `The run hit an error: ${failure}`
        : 'The run hit an error before completion.';
    default:
      return '';
  }
}

function taskSummaryFromContext(context?: Record<string, unknown>): string {
  const summary = String(context?.task_summary ?? '')
    .replace(/\s+/g, ' ')
    .trim();
  if (!summary || ['done', 'failed', 'thinking…', 'thinking...'].includes(summary.toLowerCase())) {
    return '';
  }
  return summary;
}

/** Client-side mirror of speak-API fallbacks for agent bookend milestones. */
export function agentMilestoneFallbackLine(input: {
  milestoneKey: string;
  context?: Record<string, unknown>;
}): string {
  const context = input.context ?? {};
  if (input.milestoneKey.startsWith('tool:')) {
    const toolLabel = String(context.tool_label ?? '').trim();
    return toolLabel ? toolMilestoneSpeakLine(toolLabel) : '';
  }
  if (input.milestoneKey.startsWith('edit:')) {
    const fileName = String(context.file_name ?? context.edit_path ?? '').trim();
    return fileName ? `I'm updating ${fileName}.` : '';
  }
  const eventType =
    input.milestoneKey === 'start'
      ? 'run_started'
      : input.milestoneKey === 'failed'
        ? 'agent_failed'
        : 'done';
  return progressFallbackLine({ eventType, context });
}


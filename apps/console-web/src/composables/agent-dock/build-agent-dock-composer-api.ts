import { agentExecutionAccessHint } from '../../lib/agent-execution-access-prefs';
import {
  kairoConversationError,
  kairoConversationReply,
} from '../../features/kairo-conversation/kairo-conversation-state';
import { OPERATOR_PERSONA_NAME } from '../../lib/operator-persona-name';
import { MODE_OPTIONS } from './use-composer-menus';

const COMPOSER_API_ROOT = {
  MODE_OPTIONS,
  OPERATOR_PERSONA_NAME,
  agentExecutionAccessHint,
  kairoConversationError,
  kairoConversationReply,
} as const;

export function buildAgentDockComposerApi<T extends Record<string, unknown>>(
  parts: T,
): typeof COMPOSER_API_ROOT & T {
  return {
    ...COMPOSER_API_ROOT,
    ...parts,
  } as typeof COMPOSER_API_ROOT & T;
}

export type AgentDockComposerApi = ReturnType<typeof buildAgentDockComposerApi<Record<string, never>>>;

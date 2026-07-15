import type { KairoNarrationLevel } from '../contracts/canonical';

import type { NarrationMilestone } from './kairo-agent-narration';
import {
  mapMilestoneToSpeakEvent,
  shouldNarrateAgentEvent,
} from './kairo-narration-policy';
import { agentMilestoneFallbackLine } from './kairo-progress-fallback';
import { postKairoSpeak } from './kairo-speak-client';
import { deliverSpokenOperatorAlert } from './spoken-alert-delivery';

interface CreateKairoAgentMilestoneNarratorOptions {
  messageId: string;
  sessionId: () => string;
  workspaceId: () => string;
  narration: () => KairoNarrationLevel;
  voiceDeliveryAllowed: () => boolean;
  operatorPrompt: () => string;
  fullAccess: () => boolean;
}

const SPEAK_TIMEOUT_MS = 12_000;

export function createKairoAgentMilestoneNarrator(
  options: CreateKairoAgentMilestoneNarratorOptions,
) {
  let chain = Promise.resolve();
  const spokenKeys = new Set<string>();

  function narrate(milestone: NarrationMilestone): void {
    const narration = options.narration();
    if (
      !shouldNarrateAgentEvent({ eventKey: milestone.key, narration }) ||
      !options.voiceDeliveryAllowed() ||
      narration === 'off' ||
      spokenKeys.has(milestone.key)
    ) {
      return;
    }
    spokenKeys.add(milestone.key);

    const eventType = mapMilestoneToSpeakEvent(milestone.key);
    const editPath = milestone.editPath ?? '';
    const context: Record<string, unknown> = {
      operator_prompt: options.operatorPrompt(),
      full_access: options.fullAccess(),
      task_summary: milestone.message,
      tool_label: milestone.toolLabel ?? '',
      edit_path: editPath,
      edit_count: milestone.editCount ?? 0,
      file_name: editPath ? editPath.split('/').pop() ?? editPath : '',
    };
    if (milestone.key === 'failed') {
      context.failure_summary = milestone.message;
    }

    chain = chain
      .then(async () => {
        const controller = new AbortController();
        const timeout = globalThis.setTimeout(() => controller.abort(), SPEAK_TIMEOUT_MS);
        const fallback = agentMilestoneFallbackLine({
          milestoneKey: milestone.key,
          context,
        });
        let message = milestone.verbatim
          ? milestone.message.trim()
          : fallback || milestone.message.replace(/\.$/, '').trim();
        try {
          if (!milestone.verbatim) {
            const response = await postKairoSpeak(
              {
                event_type: eventType,
                context,
                session_id: options.sessionId(),
                workspace_id: options.workspaceId(),
                narration,
                use_runtime: narration === 'conversational',
              },
              { signal: controller.signal },
            );
            if (response.source !== 'skipped' && response.line.trim()) {
              message = response.line.trim();
            }
          }
        } catch {
          if (!message) {
            message = fallback || milestone.message.replace(/\.$/, '').trim();
          }
        } finally {
          globalThis.clearTimeout(timeout);
        }

        if (!message) {
          return;
        }

        await deliverSpokenOperatorAlert(
          {
            eligible: true,
            reason: `kairo-agent:${milestone.key}`,
            signal_id: `${options.messageId}:${milestone.key}`,
            message,
          },
          sessionStorage,
          { priority: 'narration' },
        );
      })
      .catch(() => undefined);
  }

  return { narrate };
}

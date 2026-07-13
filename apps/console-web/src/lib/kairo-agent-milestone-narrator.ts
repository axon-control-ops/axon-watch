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
  const deliveredLines: Array<{ key: string; line: string }> = [];

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

        const normalizedMessage = message.toLowerCase().replace(/\s+/g, ' ').trim();
        const matchingDelivery = deliveredLines.find(
          (item) => item.line.toLowerCase().replace(/\s+/g, ' ').trim() === normalizedMessage,
        );
        // #region agent log
        fetch('http://127.0.0.1:7852/ingest/0173158c-fd82-46b4-a14c-d55e0685ee25',{method:'POST',headers:{'Content-Type':'application/json','X-Debug-Session-Id':'df24bc'},body:JSON.stringify({sessionId:'df24bc',runId:options.messageId,hypothesisId:'R1',location:'kairo-agent-milestone-narrator.ts:beforeDelivery',message:'agent milestone narration resolved',data:{key:milestone.key,line:message.slice(0,280),matchesPriorKey:matchingDelivery?.key??null,priorDeliveries:deliveredLines.map((item)=>item.key)},timestamp:Date.now()})}).catch(()=>{});
        // #endregion
        deliveredLines.push({ key: milestone.key, line: message });
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

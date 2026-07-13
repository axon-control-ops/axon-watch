import type { KairoNarrationLevel } from '../contracts/canonical';

import { shouldNarrateProgressMilestone } from './kairo-narration-policy';
import { progressFallbackLine } from './kairo-progress-fallback';
import { postKairoSpeak } from './kairo-speak-client';
import { deliverSpokenOperatorAlert } from './spoken-alert-delivery';

export interface KairoProgressMilestone {
  eventKey: string;
  eventType: string;
  context?: Record<string, unknown>;
}

interface CreateKairoProgressNarratorOptions {
  messageId: string;
  sessionId: () => string;
  workspaceId: () => string;
  narration: () => KairoNarrationLevel;
  voiceDeliveryAllowed: () => boolean;
}

const TERMINAL_RANK: Record<string, number> = {
  run_started: 1,
  research_started: 2,
  research_complete: 3,
  approval_required: 4,
  verified_complete: 5,
  unverified_complete: 5,
  stream_error: 5,
};

// Cursor CLI cold starts can take many seconds; a short timeout forces canned one-liners.
const SPEAK_TIMEOUT_MS = 12_000;

function milestoneRank(eventType: string): number {
  return TERMINAL_RANK[eventType] ?? 0;
}

export function createKairoProgressNarrator(options: CreateKairoProgressNarratorOptions) {
  let chain = Promise.resolve();
  let latestRank = 0;
  let currentRequestId = 0;

  async function resolveLine(
    milestone: KairoProgressMilestone,
    requestId: number,
  ): Promise<string | null> {
    const narration = options.narration();
    const fallback = progressFallbackLine({
      eventType: milestone.eventType,
      context: milestone.context,
    });
    if (!options.voiceDeliveryAllowed() || narration === 'off') {
      return null;
    }

    const controller = new AbortController();
    const timeout = globalThis.setTimeout(() => controller.abort(), SPEAK_TIMEOUT_MS);
    try {
      const response = await postKairoSpeak(
        {
          event_type: milestone.eventType,
          context: milestone.context ?? {},
          session_id: options.sessionId(),
          workspace_id: options.workspaceId(),
          narration,
          use_runtime: narration === 'conversational',
        },
        { signal: controller.signal },
      );
      if (requestId !== currentRequestId) {
        return null;
      }
      return response.source !== 'skipped' && response.line.trim() ? response.line.trim() : fallback;
    } catch {
      if (requestId !== currentRequestId) {
        return null;
      }
      return fallback || null;
    } finally {
      globalThis.clearTimeout(timeout);
    }
  }

  function narrate(milestone: KairoProgressMilestone): void {
    const narration = options.narration();
    if (!shouldNarrateProgressMilestone({ eventType: milestone.eventType, narration })) {
      return;
    }
    const rank = milestoneRank(milestone.eventType);
    latestRank = Math.max(latestRank, rank);
    const requestId = ++currentRequestId;
    chain = chain
      .then(async () => {
        if (requestId !== currentRequestId) {
          return;
        }
        const line = await resolveLine(milestone, requestId);
        if (!line || requestId !== currentRequestId) {
          return;
        }
        if (rank < latestRank && latestRank >= 4) {
          return;
        }
        // #region agent log
        fetch('http://127.0.0.1:7852/ingest/0173158c-fd82-46b4-a14c-d55e0685ee25',{method:'POST',headers:{'Content-Type':'application/json','X-Debug-Session-Id':'df24bc'},body:JSON.stringify({sessionId:'df24bc',runId:options.messageId,hypothesisId:'R2',location:'kairo-progress-narrator.ts:beforeDelivery',message:'progress narration resolved',data:{eventKey:milestone.eventKey,eventType:milestone.eventType,line:line.slice(0,280),rank,latestRank},timestamp:Date.now()})}).catch(()=>{});
        // #endregion
        await deliverSpokenOperatorAlert(
          {
            eligible: true,
            reason: `kairo-progress:${milestone.eventType}`,
            signal_id: `${options.messageId}:${milestone.eventKey}`,
            message: line,
          },
          sessionStorage,
          { priority: 'narration' },
        );
      })
      .catch(() => undefined);
  }

  function cancel(): void {
    currentRequestId += 1;
  }

  return {
    cancel,
    narrate,
  };
}


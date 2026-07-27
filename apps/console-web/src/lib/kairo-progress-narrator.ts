import type { KairoNarrationLevel } from '../contracts/canonical';

import { shouldNarrateProgressMilestone } from './kairo-narration-policy';
import { progressFallbackLine } from './kairo-progress-fallback';
import { postKairoSpeak } from './kairo-speak-client';
import { deliverSpokenOperatorAlert } from './spoken-alert-delivery';
import type { KairoVoiceSpeaker } from './kairo-voice-utterance';

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
  azureVoiceId?: () => string | null | undefined;
  speaker?: () => KairoVoiceSpeaker | null | undefined;
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
        await deliverSpokenOperatorAlert(
          {
            eligible: true,
            reason: `kairo-progress:${milestone.eventType}`,
            signal_id: `${options.messageId}:${milestone.eventKey}`,
            message: line,
          },
          sessionStorage,
          {
            priority: 'narration',
            azureVoiceId: options.azureVoiceId?.() ?? null,
            speaker: options.speaker?.() ?? null,
          },
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


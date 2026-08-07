/**
 * Serializes all Vaxon spoken output so signal alerts, run narration, and
 * conversation replies never overlap or clip each other mid-word.
 *
 * Only barge-in (`interrupt`) flushes the queue and stops current playback.
 */
import {
  playKairoUtteranceNow,
  stopKairoPlayback,
  type KairoVoicePlaybackResult,
} from './kairo-voice-playback';
import type { KairoVoiceSpeaker } from './kairo-voice-utterance';
import { reportTheaterOpen } from '../features/report-theater/report-theater-state';

export type KairoVoicePriority =
  | 'interrupt'
  | 'alert'
  | 'conversation'
  | 'narration';

export type EnqueueKairoSpeechOptions = {
  priority?: KairoVoicePriority;
  preferBrowser?: boolean;
  speechRate?: number;
  speechPitch?: number;
  azureVoiceId?: string;
  speaker?: KairoVoiceSpeaker;
  /** Command Theater narration — only this lane may speak while stand-up is open. */
  allowDuringReportTheater?: boolean;
  /** Cap Azure wait before falling back to browser TTS (ms). */
  ttsTimeoutMs?: number;
  /** Fires once when audible playback begins. */
  onPlaybackStart?: () => void;
};

type VoiceJob = {
  id: number;
  text: string;
  priority: KairoVoicePriority;
  preferBrowser: boolean;
  speechRate?: number;
  speechPitch?: number;
  azureVoiceId?: string;
  speaker?: KairoVoiceSpeaker;
  ttsTimeoutMs?: number;
  onPlaybackStart?: () => void;
  resolve: (result: KairoVoicePlaybackResult) => void;
  reject: (error: unknown) => void;
};

const PRIORITY_RANK: Record<KairoVoicePriority, number> = {
  interrupt: 0,
  alert: 1,
  conversation: 2,
  narration: 3,
};

const POST_UTTERANCE_SETTLE_MS = 150;

let nextJobId = 0;
let activeJob: VoiceJob | null = null;
let pending: VoiceJob[] = [];
let pumping = false;
const debugVoiceRealmId =
  typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function'
    ? crypto.randomUUID()
    : `voice-realm-${Date.now()}-${Math.random().toString(36).slice(2)}`;

function debugTokenOverlap(left: string, right: string): number {
  const tokens = (text: string) =>
    new Set(text.toLowerCase().match(/[a-z0-9]{3,}/g) ?? []);
  const leftTokens = tokens(left);
  const rightTokens = tokens(right);
  if (!leftTokens.size || !rightTokens.size) {
    return 0;
  }
  let shared = 0;
  for (const token of leftTokens) {
    if (rightTokens.has(token)) {
      shared += 1;
    }
  }
  return shared / Math.min(leftTokens.size, rightTokens.size);
}

function sortPending(): void {
  pending.sort((a, b) => {
    const rank = PRIORITY_RANK[a.priority] - PRIORITY_RANK[b.priority];
    return rank !== 0 ? rank : a.id - b.id;
  });
}

function dropWaitingNarration(reason: string): void {
  const kept: VoiceJob[] = [];
  for (const job of pending) {
    if (job.priority === 'narration') {
      job.resolve({ engine: 'skipped', reason: reason.slice(0, 120) });
      continue;
    }
    kept.push(job);
  }
  pending = kept;
}

/** Drop queued narration jobs when a run advances past a stale milestone. */
export function dropWaitingKairoNarration(reason = 'stale_run_advance'): void {
  dropWaitingNarration(reason);
}

/**
 * Drop waiting narration and stop an already-playing narration utterance.
 * Used when a stream ends so mid-run "I am checking…" cannot keep speaking
 * after Done / ask. Does not cut alerts or conversation replies.
 */
export function stopActiveKairoNarration(reason = 'stream_complete'): void {
  dropWaitingNarration(reason);
  if (activeJob?.priority === 'narration') {
    stopKairoPlayback();
  }
}

async function settleAfterUtterance(): Promise<void> {
  await new Promise<void>((resolve) => {
    globalThis.setTimeout(resolve, POST_UTTERANCE_SETTLE_MS);
  });
}

async function pump(): Promise<void> {
  if (pumping) {
    return;
  }
  pumping = true;
  try {
    while (pending.length > 0) {
      sortPending();
      const job = pending.shift();
      if (!job) {
        break;
      }
      activeJob = job;
      // #region agent log
      fetch('http://127.0.0.1:7706/ingest/90bcaec2-2b39-4d4a-84b5-157c12735440', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-Debug-Session-Id': '9e41d8' },
        body: JSON.stringify({
          sessionId: '9e41d8',
          hypothesisId: 'H3_playback_overlap',
          location: 'kairo-voice-queue.ts:pump:dequeue',
          message: 'queue job dequeued for playback',
          data: {
            debugVoiceRealmId,
            jobId: job.id,
            priority: job.priority,
            speakerId: job.speaker?.id ?? null,
            textPreview: job.text.slice(0, 80),
            pendingAfter: pending.length,
            documentVisibility:
              typeof document === 'undefined' ? null : document.visibilityState,
          },
          timestamp: Date.now(),
        }),
      }).catch(() => {});
      // #endregion agent log
      try {
        const result = await playKairoUtteranceNow(job.text, {
          preferBrowser: job.preferBrowser,
          speechRate: job.speechRate,
          speechPitch: job.speechPitch,
          azureVoiceId: job.azureVoiceId,
          speaker: job.speaker,
          ttsTimeoutMs: job.ttsTimeoutMs,
          onPlaybackStart: job.onPlaybackStart,
        });
        await settleAfterUtterance();
        job.resolve(result);
      } catch (error) {
        job.reject(error);
      } finally {
        activeJob = null;
      }
    }
  } finally {
    pumping = false;
    if (pending.length > 0) {
      void pump();
    }
  }
}

export function isKairoSpeechQueueBusy(): boolean {
  return activeJob !== null || pending.length > 0 || pumping;
}

export function flushKairoSpeechQueue(reason = 'flush'): void {
  const dropped = pending.splice(0, pending.length);
  for (const job of dropped) {
    job.resolve({
      engine: 'skipped',
      reason: reason.slice(0, 120),
    });
  }
}

/**
 * Stop current playback and clear waiting jobs (operator barge-in / mic open).
 */
export async function interruptKairoSpeechQueue(
  reason = 'barge_in',
): Promise<void> {
  flushKairoSpeechQueue(reason);
  await stopKairoPlayback();
}

/**
 * Queue a line for exclusive playback. Higher-priority jobs jump ahead of
 * waiting lower-priority ones; only `interrupt` cancels what is already playing.
 */
export function enqueueKairoSpeech(
  text: string,
  options: EnqueueKairoSpeechOptions = {},
): Promise<KairoVoicePlaybackResult> {
  const trimmed = String(text || '').trim();
  const priority = options.priority ?? 'conversation';
  if (!trimmed) {
    return Promise.resolve({ engine: 'skipped', reason: 'empty' });
  }

  // Hard mute: nothing barges into Command Theater except the stand-up lane.
  if (
    reportTheaterOpen.value &&
    !options.allowDuringReportTheater &&
    priority !== 'interrupt'
  ) {
    return Promise.resolve({ engine: 'skipped', reason: 'report_theater_lock' });
  }

  return new Promise<KairoVoicePlaybackResult>((resolve, reject) => {
    const job: VoiceJob = {
      id: ++nextJobId,
      text: trimmed,
      priority,
      preferBrowser: options.preferBrowser === true,
      speechRate: options.speechRate,
      speechPitch: options.speechPitch,
      azureVoiceId: options.azureVoiceId,
      speaker: options.speaker,
      ttsTimeoutMs: options.ttsTimeoutMs,
      onPlaybackStart: options.onPlaybackStart,
      resolve,
      reject,
    };
    const activeTokenOverlap = activeJob
      ? debugTokenOverlap(activeJob.text, job.text)
      : 0;
    // #region agent log
    fetch('http://127.0.0.1:7706/ingest/90bcaec2-2b39-4d4a-84b5-157c12735440', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-Debug-Session-Id': '9e41d8' },
      body: JSON.stringify({
        sessionId: '9e41d8',
        hypothesisId: 'H3_playback_overlap',
        location: 'kairo-voice-queue.ts:enqueueKairoSpeech',
        message: 'job enqueued',
        data: {
          debugVoiceRealmId,
          jobId: job.id,
          priority,
          speakerId: job.speaker?.id ?? null,
          textPreview: job.text.slice(0, 180),
          activeJobId: activeJob?.id ?? null,
          activeSpeakerId: activeJob?.speaker?.id ?? null,
          activePriority: activeJob?.priority ?? null,
          activeTokenOverlap,
          pendingBefore: pending.length,
          documentVisibility:
            typeof document === 'undefined' ? null : document.visibilityState,
        },
        timestamp: Date.now(),
      }),
    }).catch(() => {});
    // #endregion agent log
    if (priority === 'interrupt') {
      flushKairoSpeechQueue('preempted_by_interrupt');
      void stopKairoPlayback();
      pending.unshift(job);
    } else if (priority === 'alert') {
      // Alerts jump ahead of waiting narration so a signal is not buried under
      // run chatter. Never cut an utterance that has already started.
      dropWaitingNarration('preempted_by_alert');
      pending.push(job);
      sortPending();
    } else {
      pending.push(job);
      sortPending();
    }

    void pump();
  });
}

/** Test helper — reset queue state between cases. */
export function resetKairoSpeechQueueForTests(): void {
  pending = [];
  activeJob = null;
  pumping = false;
  nextJobId = 0;
}

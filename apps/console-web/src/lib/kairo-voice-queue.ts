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

export type KairoVoicePriority =
  | 'interrupt'
  | 'alert'
  | 'conversation'
  | 'narration';

export type EnqueueKairoSpeechOptions = {
  priority?: KairoVoicePriority;
  preferBrowser?: boolean;
};

type VoiceJob = {
  id: number;
  text: string;
  priority: KairoVoicePriority;
  preferBrowser: boolean;
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
      try {
        const result = await playKairoUtteranceNow(job.text, {
          preferBrowser: job.preferBrowser,
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

  return new Promise<KairoVoicePlaybackResult>((resolve, reject) => {
    const job: VoiceJob = {
      id: ++nextJobId,
      text: trimmed,
      priority,
      preferBrowser: options.preferBrowser === true,
      resolve,
      reject,
    };

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

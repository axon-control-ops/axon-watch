import type { ReportTheaterStage } from './report-theater-model';
import { isReportTheaterFillerLine, stageSpokenLine } from './report-theater-directives';

export type ReportTheaterNarrationHooks = {
  speak: (line: string) => Promise<void>;
  setStageIndex: (index: number) => void;
  onComplete: () => void;
  /** Fired after next-move speech so VAXON can execute the commitment. */
  onCommitted?: () => void | Promise<void>;
  isCancelled: () => boolean;
};

function stageIsFiller(stage: ReportTheaterStage): boolean {
  return stage.lines.every((line) => isReportTheaterFillerLine(line));
}

/**
 * Speak one stand-up section at a time and advance the theater only after
 * each utterance finishes — keeps voice and panels locked together.
 */
export async function narrateReportTheater(
  stages: ReportTheaterStage[],
  hooks: ReportTheaterNarrationHooks,
): Promise<void> {
  if (hooks.isCancelled()) {
    return;
  }
  await hooks.speak("Here's the stand-up.");
  if (hooks.isCancelled()) {
    return;
  }

  for (let index = 0; index < stages.length; index += 1) {
    if (hooks.isCancelled()) {
      return;
    }
    const stage = stages[index];
    if (!stage) {
      continue;
    }
    hooks.setStageIndex(index);
    const line = stageSpokenLine(stage.title, stage.lines);
    // Filler boards get a flash + short beat, not a long dwell.
    if (stageIsFiller(stage) && stage.id !== 'next_move') {
      await hooks.speak(line);
      continue;
    }
    await hooks.speak(line);
  }

  if (hooks.isCancelled()) {
    return;
  }
  hooks.onComplete();
  if (hooks.onCommitted) {
    await hooks.onCommitted();
  }
}

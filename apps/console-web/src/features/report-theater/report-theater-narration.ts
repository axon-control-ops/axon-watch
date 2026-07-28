import type { ReportTheaterStage } from './report-theater-model';
import { isReportTheaterFillerLine, stageSpokenLine } from './report-theater-directives';

export type ReportTheaterNarrationHooks = {
  speak: (line: string, speakerName?: string | null) => Promise<void>;
  setStageIndex: (index: number) => void;
  onComplete: () => void;
  /** Fired after next-move speech so VAXON can execute the commitment. */
  onCommitted?: () => void | Promise<void>;
  isCancelled: () => boolean;
};

function stageIsFiller(stage: ReportTheaterStage): boolean {
  return stage.lines.every((line) => isReportTheaterFillerLine(line));
}

type TheaterSpeechTurn = { line: string; speakerName: string | null };

const MAX_SPOKEN_BODY = 140;

/** Operator-facing scrub for board cards and TTS — strip CLI laundry lists. */
export function polishTheaterLine(body: string, maxChars = MAX_SPOKEN_BODY): string {
  let cleaned = String(body || '')
    .replace(/\binvocation\s*id[:,]?\s*[a-f0-9-]+/gi, '')
    .replace(/\bunit:\s*[\w.-]+/gi, '')
    .replace(/\bscope[,:]?\s*[\w.-]+/gi, '')
    .replace(/\bauth\s*=\s*missing\b/gi, 'authentication is missing')
    .replace(/\bopen\s+runtime\s+or\s+\/vault\b/gi, 'open Runtime or Vault')
    .replace(/\s*—\s*/g, '. ')
    .replace(/\s*;\s*/g, '. ')
    .replace(/\s+/g, ' ')
    .trim();

  if (/no cli runtime is ready|cli\s*\(local\)\s*unavailable/i.test(cleaned)) {
    cleaned = cleaned.replace(
      /cannot start because no CLI runtime is ready.*/i,
      'cannot start — no CLI runtime is ready. Open Runtime or Vault, then retry',
    );
    cleaned = cleaned.replace(/:\s*Codex CLI.*/i, '. Open Runtime or Vault, then retry');
  }
  if (/failed on cursor cli/i.test(cleaned)) {
    cleaned = cleaned.replace(
      /failed on Cursor CLI.*/i,
      'failed on Cursor CLI — runtime login is not ready',
    );
  }
  if (/^just completed$/i.test(cleaned)) {
    return 'I just completed my shift';
  }
  if (cleaned.length <= maxChars) {
    return cleaned;
  }
  const cut = cleaned.slice(0, maxChars - 1);
  const boundary = Math.max(cut.lastIndexOf('. '), cut.lastIndexOf(', '), cut.lastIndexOf(' '));
  return `${(boundary > 40 ? cut.slice(0, boundary) : cut).trim()}…`;
}

function attributedStageTurns(stage: ReportTheaterStage): TheaterSpeechTurn[] | null {
  const concrete = stage.lines
    .map((line) => line.trim().replace(/\.+$/, ''))
    .filter(Boolean)
    .filter((line) => !isReportTheaterFillerLine(line));
  if (!concrete.length || !['work_in_flight', 'lead_rollups'].includes(stage.id)) {
    return null;
  }
  const turns: TheaterSpeechTurn[] = [
    {
      line: stage.id === 'lead_rollups' ? 'Lead reports.' : `${stage.title}.`,
      speakerName: null,
    },
  ];
  for (const line of concrete.slice(0, 2)) {
    const leadMatch = line.match(/^([^:]+):\s*(.+)$/);
    const employeeMatch = line.match(/^([^:(]+)\s*\([^)]*\)\s+(.+)$/);
    const name = (leadMatch?.[1] ?? employeeMatch?.[1] ?? '').trim();
    const spokenBody = polishTheaterLine(leadMatch?.[2] ?? employeeMatch?.[2] ?? line);
    turns.push({
      line: name ? `${name} here. ${spokenBody}.` : `${spokenBody}.`,
      speakerName: name || null,
    });
  }
  return turns;
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
  await hooks.speak('Stand-up online.');
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
    const attributedTurns = attributedStageTurns(stage);
    if (attributedTurns) {
      for (const turn of attributedTurns) {
        // #region agent log
        fetch('http://127.0.0.1:7706/ingest/90bcaec2-2b39-4d4a-84b5-157c12735440',{method:'POST',headers:{'Content-Type':'application/json','X-Debug-Session-Id':'bef50e'},body:JSON.stringify({sessionId:'bef50e',runId:'jarvis-polish',hypothesisId:'H52,H53',location:'report-theater-narration.ts:turn',message:'speaking polished theater turn',data:{stageId:stage.id,speaker:turn.speakerName,lineChars:turn.line.length,linePreview:turn.line.slice(0,160)},timestamp:Date.now()})}).catch(()=>{});
        // #endregion
        await hooks.speak(turn.line, turn.speakerName);
      }
      continue;
    }
    const line = polishTheaterLine(stageSpokenLine(stage.title, stage.lines), 180);
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

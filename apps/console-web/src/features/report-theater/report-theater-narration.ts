import type { ReportTheaterStage } from './report-theater-model';
import { isReportTheaterFillerLine, stageSpokenLine } from './report-theater-directives';

export type ReportTheaterNarrationHooks = {
  speak: (
    line: string,
    speakerName?: string | null,
    onPlaybackStart?: () => void,
  ) => Promise<void>;
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

/** Keep Lead turns brisk; the full receipt remains visible on the board. */
const MAX_SPOKEN_BODY = 220;

const SHELL_DUMP_SPLIT =
  /\s+(?:terminal\b|ls\s+-la\b|find\s+\/|cat\s+\/|grep\s+|head\s+-|2>\/dev\/null)/i;

function pushFailureSummary(text: string): string | null {
  const hay = text.toLowerCase();
  if (!/push failed|git push failed|push did not|retry the push/i.test(hay)) {
    return null;
  }
  if (/protected branch|branch protection|pull request/i.test(hay)) {
    return 'Commit landed; direct push was blocked by branch protection';
  }
  if (/non-fast-forward|fetch first|updates were rejected|branch is behind/i.test(hay)) {
    return 'Commit landed; push was rejected because the remote branch is ahead';
  }
  if (/authentication failed|permission denied|invalid credentials|repository not found|http 40[13]/i.test(hay)) {
    return 'Commit landed; push was rejected by Git authentication or permissions';
  }
  if (/could not resolve host|timed out|connection reset|network is unreachable|failed to connect/i.test(hay)) {
    return 'Commit landed; push could not reach the remote';
  }
  if (/pre-receive hook|pre-push hook|hook declined/i.test(hay)) {
    return 'Commit landed; a push hook rejected it';
  }
  return 'Commit landed; push did not. Inspect the Lead receipt for the exact error';
}

/** Operator-facing scrub for board cards and TTS — strip CLI laundry lists. */
export function polishTheaterLine(body: string, maxChars = MAX_SPOKEN_BODY): string {
  const pushSummary = pushFailureSummary(body);
  let cleaned = String(body || '')
    .replace(/\binvocation\s*id[:,]?\s*[a-f0-9-]+/gi, '')
    .replace(/\bunit:\s*[\w.-]+/gi, '')
    .replace(/\bscope[,:]?\s*[\w.-]+/gi, '')
    .replace(/\bauth\s*=\s*missing\b/gi, 'authentication is missing')
    .replace(/\bopen\s+runtime\s+or\s+\/vault\b/gi, 'open Runtime or Vault')
    .replace(
      /committed successfully with message:\s*selected option\s+\S+\s*:\s*/gi,
      'Committed after your choice — ',
    )
    .replace(/committed successfully with message:\s*/gi, 'Committed — ')
    .replace(/selected option\s+\S+\s*:\s*/gi, '')
    .trim();
  if (pushSummary) {
    cleaned = cleaned.replace(
      /(?:push failed:\s*)?git push failed(?:\s*:\s*)?.*$/i,
      pushSummary,
    );
  }
  cleaned = cleaned
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
  // Strip shell/path laundry that Leads sometimes paste into handoff headlines.
  if (SHELL_DUMP_SPLIT.test(cleaned) || /\/home\/\w+\//.test(cleaned) || /\.sqlite3?\b/i.test(cleaned)) {
    cleaned = cleaned.split(SHELL_DUMP_SPLIT)[0]?.trim().replace(/[.]+$/, '').trim() || '';
    if (/\/home\/\w+\//.test(cleaned)) {
      cleaned = cleaned.split(/\s+\/home\//i)[0]?.trim().replace(/[.]+$/, '').trim() || '';
    }
    if (!cleaned) {
      cleaned = 'Shift completed — details are in the Lead receipts';
    } else if (!/[.!?]$/.test(cleaned)) {
      cleaned = `${cleaned}.`;
    }
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
    const attributedTurns = attributedStageTurns(stage);
    let stageStarted = false;
    const startStage = () => {
      if (stageStarted) {
        return;
      }
      stageStarted = true;
      hooks.setStageIndex(index);
    };
    if (attributedTurns) {
      for (const turn of attributedTurns) {
        await hooks.speak(turn.line, turn.speakerName, startStage);
      }
      continue;
    }
    const line = polishTheaterLine(stageSpokenLine(stage.title, stage.lines), 180);
    if (stageIsFiller(stage) && stage.id !== 'next_move') {
      await hooks.speak(line, null, startStage);
      continue;
    }
    await hooks.speak(line, null, startStage);
  }

  if (hooks.isCancelled()) {
    return;
  }
  hooks.onComplete();
  if (hooks.onCommitted) {
    await hooks.onCommitted();
  }
}

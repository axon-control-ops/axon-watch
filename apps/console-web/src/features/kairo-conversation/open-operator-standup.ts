import { navigateToAppSurface } from '../../lib/app-surface-route';
import { submitKairoConversationTranscript } from './kairo-conversation-bus';
import { reportTheaterOpen } from '../report-theater/report-theater-state';

type StandupShell = {
  layoutMode?: string;
  setLayoutMode?: (mode: 'operator' | 'ide') => void;
};

/**
 * Re-open Command Theater stand-up from any surface (IDE, Vault, Settings, …).
 * Returns to Console first so ReportTheaterOverlay is mounted, then submits REPORT.
 */
export async function openOperatorStandup(shell?: StandupShell | null): Promise<void> {
  navigateToAppSurface('console');
  // Mission Control Live Ops is the natural stand-up home; IDE still mounts theater.
  if (shell?.layoutMode === 'ide' && typeof shell.setLayoutMode === 'function') {
    shell.setLayoutMode('operator');
  }
  if (reportTheaterOpen.value) {
    // Already open — restart with a fresh REPORT turn.
  }
  await submitKairoConversationTranscript('REPORT');
}

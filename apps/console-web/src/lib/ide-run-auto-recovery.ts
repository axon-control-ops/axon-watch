import {
  clearIdeRunRecovery,
  decideIdeRunRecovery,
  fetchControlPlaneBootId,
  persistIdeRunRecovery,
  SERVER_RESTART_CONTINUATION_PROMPT,
  waitForStableControlPlaneBootId,
  type IdeRunRecoveryRecord,
} from './ide-run-recovery';

type ContinuationInput = {
  mode: IdeRunRecoveryRecord['mode'];
  content: string;
  linkedRunId: string | null;
  threadId: string;
  recoveryCount: number;
};

export async function executeIdeRunRecovery(options: {
  recovery: IdeRunRecoveryRecord;
  loadRunPhase: () => Promise<string | null>;
  streamActive: () => boolean;
  mutationBusy: () => boolean;
  currentWorkspaceId: () => string | null;
  linkRun: (runId: string) => void;
  reattach: (recovery: IdeRunRecoveryRecord) => Promise<void>;
  reportError: (message: string) => void;
  dispatchContinuation: (input: ContinuationInput) => Promise<boolean>;
  waitForBootId?: (previousBootId: string) => Promise<string | null>;
  fetchBootId?: () => Promise<string>;
  clearRecovery?: (runId: string) => void;
  persistRecovery?: (recovery: IdeRunRecoveryRecord) => void;
}): Promise<void> {
  const { recovery } = options;
  let currentBootId =
    (await (
      options.waitForBootId
        ? options.waitForBootId(recovery.controlPlaneBootId)
        : waitForStableControlPlaneBootId({
            previousBootId: recovery.controlPlaneBootId,
          })
    )) ?? '';
  const runPhase = await options.loadRunPhase();

  if (!currentBootId) {
    try {
      currentBootId = await (options.fetchBootId?.() ?? fetchControlPlaneBootId());
    } catch {
      currentBootId = recovery.controlPlaneBootId;
    }
  }

  const decision = decideIdeRunRecovery({
    recovery,
    currentBootId,
    runPhase,
    streamActive: options.streamActive(),
    mutationBusy: options.mutationBusy(),
    currentWorkspaceId: options.currentWorkspaceId(),
  });

  if (decision.action === 'clear') {
    (options.clearRecovery ?? clearIdeRunRecovery)(recovery.runId);
    return;
  }
  if (decision.action === 'stop_retry') {
    (options.clearRecovery ?? clearIdeRunRecovery)(recovery.runId);
    options.reportError(decision.reason);
    return;
  }
  if (decision.action === 'reattach') {
    await options.reattach(recovery);
    return;
  }
  if (decision.action !== 'continue') {
    return;
  }

  if (decision.linkExistingRun) {
    options.linkRun(recovery.runId);
  }
  (options.clearRecovery ?? clearIdeRunRecovery)(recovery.runId);
  const dispatched = await options.dispatchContinuation({
    mode: recovery.mode,
    content: SERVER_RESTART_CONTINUATION_PROMPT,
    linkedRunId: decision.linkExistingRun ? recovery.runId : null,
    threadId: recovery.threadId,
    recoveryCount: decision.nextRecoveryCount,
  });
  if (!dispatched) {
    (options.persistRecovery ?? persistIdeRunRecovery)({
      ...recovery,
      recoveryCount: decision.nextRecoveryCount - 1,
    });
  }
}

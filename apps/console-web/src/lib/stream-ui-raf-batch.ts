export type RafStreamUiBatcher<TPartial> = {
  schedule: (workspaceId: string, partial: TPartial) => void;
  flushNow: (workspaceId: string) => void;
  cancel: (workspaceId: string) => void;
};

/** Coalesce rapid stream UI patches to one flush per animation frame. */
export function createRafStreamUiBatcher<TPartial>(
  flush: (workspaceId: string, partial: TPartial) => void,
  requestFrame: (callback: FrameRequestCallback) => number = requestAnimationFrame,
  cancelFrame: (id: number) => void = cancelAnimationFrame,
): RafStreamUiBatcher<TPartial> {
  const pendingByWorkspace = new Map<string, TPartial>();
  const rafByWorkspace = new Map<string, number>();

  function flushOne(workspaceId: string): void {
    rafByWorkspace.delete(workspaceId);
    const partial = pendingByWorkspace.get(workspaceId);
    if (!partial) {
      return;
    }
    pendingByWorkspace.delete(workspaceId);
    flush(workspaceId, partial);
  }

  return {
    schedule(workspaceId, partial) {
      pendingByWorkspace.set(workspaceId, partial);
      if (!rafByWorkspace.has(workspaceId)) {
        const frameId = requestFrame(() => flushOne(workspaceId));
        rafByWorkspace.set(workspaceId, frameId);
      }
    },
    flushNow(workspaceId) {
      const frameId = rafByWorkspace.get(workspaceId);
      if (frameId !== undefined) {
        cancelFrame(frameId);
      }
      flushOne(workspaceId);
    },
    cancel(workspaceId) {
      const frameId = rafByWorkspace.get(workspaceId);
      if (frameId !== undefined) {
        cancelFrame(frameId);
      }
      rafByWorkspace.delete(workspaceId);
      pendingByWorkspace.delete(workspaceId);
    },
  };
}

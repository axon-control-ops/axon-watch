export type OrbPointerUpIntent = {
  captureActive: boolean;
  handsFreeEnabled: boolean;
  heldMs: number;
  holdToTalkMs: number;
};

export type OrbPointerUpResolution = {
  stopCapture: boolean;
  suppressToggleClick: boolean;
};

/**
 * Hands-free taps should still toggle modes even while the shared mic loop is
 * actively listening. Only manual hold-to-talk interactions should consume the
 * click to stop capture or suppress a tap-toggle.
 */
export function resolveOrbPointerUpIntent(
  intent: OrbPointerUpIntent,
): OrbPointerUpResolution {
  if (intent.captureActive) {
    if (intent.handsFreeEnabled) {
      return {
        stopCapture: false,
        suppressToggleClick: false,
      };
    }
    return {
      stopCapture: true,
      suppressToggleClick: true,
    };
  }

  return {
    stopCapture: false,
    suppressToggleClick: intent.heldMs >= intent.holdToTalkMs,
  };
}

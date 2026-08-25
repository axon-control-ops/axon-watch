export type MobileTunnelActionState = {
  startDisabled: boolean;
  stopDisabled: boolean;
  running: boolean;
};

export function mobileTunnelActionState(input: {
  url: string | null;
  loading: boolean;
  mutationPending: boolean;
}): MobileTunnelActionState {
  const running = Boolean(input.url?.trim());
  return {
    running,
    startDisabled: input.loading || input.mutationPending || running,
    stopDisabled: input.loading || input.mutationPending || !running,
  };
}

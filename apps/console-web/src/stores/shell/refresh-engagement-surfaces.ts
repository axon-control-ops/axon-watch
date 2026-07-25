/** Quiet refresh after Lead rollups / review_ready material_change events. */

export async function runEngagementSurfaceRefresh(input: {
  workspaceId: string | null;
  briefingLoaded: boolean;
  loadRuns: (options: { sync: boolean }) => Promise<void>;
  loadOperatorBriefing: (options: { background: boolean }) => Promise<void>;
  refreshOperatorThreadMessages: (workspaceId: string) => Promise<void>;
}): Promise<void> {
  await Promise.all([
    input.loadRuns({ sync: false }),
    input.loadOperatorBriefing({ background: input.briefingLoaded }),
    input.workspaceId
      ? input.refreshOperatorThreadMessages(input.workspaceId)
      : Promise.resolve(),
  ]);
}

/**
 * Resolve where "Review now" should navigate — the VAXON chat message that
 * carries a Lead plan's rollup, once Lead has posted one. Extracted as a
 * pure function (mirrors resolveTaskBoardStartTarget's shape) so the
 * decision is unit-testable without mounting OperatorTaskBoardPanel.vue.
 */

export type VaxonReviewPlan = {
  vaxon_handoff?: { thread_id: string; message_id: string } | null;
};

export type VaxonReviewTarget =
  | { kind: "open_thread"; threadId: string }
  | { kind: "not_ready"; reason: string };

const NOT_READY_REASON =
  "Lead hasn't posted a rollup for this plan yet — check back once the plan reaches Awaiting engagement.";

export function resolveVaxonReviewTarget(
  plan: VaxonReviewPlan | null | undefined,
): VaxonReviewTarget {
  const threadId = String(plan?.vaxon_handoff?.thread_id || "").trim();
  if (threadId) {
    return { kind: "open_thread", threadId };
  }
  return { kind: "not_ready", reason: NOT_READY_REASON };
}

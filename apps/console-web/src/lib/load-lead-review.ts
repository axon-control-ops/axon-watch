import { fetchLeadPlan } from '../api/lead-plans-api';
import { fetchThreadHistory } from '../api/chat-api';
import { parseLeadReviewMessage, type LeadReviewParsed } from './lead-review-rollups';
import { resolveVaxonReviewTarget } from './operator-task-board-vaxon-review';
import { summarizeTaskBoardLabel } from './operator-task-board-view';

export type LeadReviewOverlayPayload = {
  planId: string;
  planGoal: string;
  planLabel: string;
  threadId: string;
  messageId: string;
  content: string;
  parsed: LeadReviewParsed;
  createdAt: string | null;
};

export type LoadLeadReviewResult =
  | { ok: true; payload: LeadReviewOverlayPayload }
  | { ok: false; error: string };

export async function loadLeadReviewFromPlan(planId: string): Promise<LoadLeadReviewResult> {
  const cleaned = String(planId || '').trim();
  if (!cleaned) {
    return { ok: false, error: 'Missing Lead plan id.' };
  }

  const plan = await fetchLeadPlan(cleaned);
  const target = resolveVaxonReviewTarget(plan);
  if (target.kind !== 'open_thread') {
    return { ok: false, error: target.reason };
  }

  const history = await fetchThreadHistory(target.threadId);
  const message =
    history.items.find((item) => item.message_id === target.messageId)
    ?? [...history.items]
      .reverse()
      .find((item) => item.role !== 'operator' && String(item.content || '').trim());

  const content = String(message?.content || '').trim();
  if (!content) {
    return {
      ok: false,
      error: 'Lead rollup message is empty or missing from the VAXON thread.',
    };
  }

  const planGoal = String(plan.goal || '').trim() || 'Lead plan';
  return {
    ok: true,
    payload: {
      planId: cleaned,
      planGoal,
      planLabel: summarizeTaskBoardLabel(planGoal),
      threadId: target.threadId,
      messageId: message?.message_id ?? target.messageId,
      content,
      parsed: parseLeadReviewMessage(content),
      createdAt: message?.created_at ?? null,
    },
  };
}

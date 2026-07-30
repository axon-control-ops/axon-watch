/**
 * After Task Board START, open the owning specialist (never leave Lead focused by accident).
 */

export type TaskBoardStartEmployee = {
  employee_id: string;
  name: string;
  role: string;
  role_label?: string;
};

export type TaskBoardStartTarget = {
  threadId: string | null;
  employee: TaskBoardStartEmployee | null;
  ownerRole: string;
};

/** Resolve who should receive focus after an operator Start. */
export function resolveTaskBoardStartTarget(input: {
  ownerRole: string | null | undefined;
  threadId?: string | null;
  roster: readonly TaskBoardStartEmployee[];
}): TaskBoardStartTarget {
  const ownerRole =
    String(input.ownerRole || "")
      .trim()
      .toLowerCase() || "watcher";
  const threadId = String(input.threadId || "").trim() || null;
  const employee =
    input.roster.find(
      (row) =>
        String(row.role || "")
          .trim()
          .toLowerCase() === ownerRole,
    ) ?? null;
  return { threadId, employee, ownerRole };
}

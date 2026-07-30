import { describe, expect, it } from "vitest";

import { resolveTaskBoardStartTarget } from "./operator-task-board-start-route";

const roster = [
  { employee_id: "e_lead", name: "Dana", role: "lead", role_label: "Lead" },
  {
    employee_id: "e_watch",
    name: "Cass",
    role: "watcher",
    role_label: "Watcher",
  },
  {
    employee_id: "e_back",
    name: "Marco",
    role: "backend",
    role_label: "Backend",
  },
] as const;

describe("resolveTaskBoardStartTarget", () => {
  it("prefers the specialist matching owner_role over Lead", () => {
    expect(
      resolveTaskBoardStartTarget({
        ownerRole: "backend",
        threadId: "thread_marco",
        roster,
      }),
    ).toEqual({
      threadId: "thread_marco",
      employee: roster[2],
      ownerRole: "backend",
    });
  });

  it("defaults blank owner_role to watcher, not lead", () => {
    const target = resolveTaskBoardStartTarget({
      ownerRole: "",
      roster,
    });
    expect(target.ownerRole).toBe("watcher");
    expect(target.employee?.employee_id).toBe("e_watch");
  });

  it("resolves Lead only when the ticket is Lead-owned", () => {
    const target = resolveTaskBoardStartTarget({
      ownerRole: "lead",
      roster,
    });
    expect(target.employee?.employee_id).toBe("e_lead");
  });
});

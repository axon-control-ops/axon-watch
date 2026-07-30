import { afterEach, describe, expect, it } from 'vitest';

import {
  clearDismissedDoneTaskIds,
  dismissDoneTaskId,
  dismissDoneTaskIds,
  loadDismissedDoneTaskIds,
} from './task-board-dismissed-done';

describe('task-board-dismissed-done', () => {
  afterEach(() => {
    clearDismissedDoneTaskIds();
  });

  it('persists dismissed completed task ids in session storage', () => {
    const first = dismissDoneTaskId('task_a', new Set());
    expect([...first]).toEqual(['task_a']);
    expect([...loadDismissedDoneTaskIds()]).toEqual(['task_a']);

    const second = dismissDoneTaskIds(['task_b', 'task_c'], first);
    expect(second.has('task_a')).toBe(true);
    expect(second.has('task_b')).toBe(true);
    expect(second.has('task_c')).toBe(true);
  });
});

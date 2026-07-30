import type { TaskBoardColumnId } from '../../../lib/operator-task-board-view';

export function columnTone(columnId: TaskBoardColumnId): string {
  if (columnId === 'needs_attention') {
    return 'needs';
  }
  if (columnId === 'in_progress') {
    return 'live';
  }
  if (columnId === 'done') {
    return 'done';
  }
  return 'waiting';
}

export function parseDependencies(raw: string): string[] {
  return raw
    .split(/[\s,]+/)
    .map((part) => part.trim())
    .filter(Boolean);
}

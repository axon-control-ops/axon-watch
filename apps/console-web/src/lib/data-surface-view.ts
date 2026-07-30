export interface DataTableSnapshot<T = Record<string, unknown>> {
  total: number;
  count: number;
  items: T[];
}

export interface OperatorDataSnapshot {
  updated_at: string;
  control_plane: {
    runs: DataTableSnapshot;
    chat_threads: DataTableSnapshot;
    chat_messages: DataTableSnapshot;
    handoffs: DataTableSnapshot;
  };
  watch: {
    commands?: DataTableSnapshot;
    events?: DataTableSnapshot;
    receipts?: DataTableSnapshot;
    suppressions?: DataTableSnapshot;
  };
}

export interface DataSurfaceTableSpec {
  id: string;
  label: string;
  total: number;
  count: number;
  columns: string[];
  rows: Record<string, unknown>[];
}

const RUN_COLUMNS = [
  'run_id',
  'workspace_id',
  'status',
  'phase',
  'summary',
  'updated_at',
] as const;

const THREAD_COLUMNS = ['thread_id', 'workspace_id', 'run_id', 'updated_at'] as const;

const MESSAGE_COLUMNS = ['role', 'workspace_id', 'content_preview', 'created_at'] as const;

const HANDOFF_COLUMNS = [
  'handoff_id',
  'source_workspace_id',
  'target_workspace_id',
  'status',
  'target_task_id',
  'routed_role',
  'task',
  'created_at',
] as const;

const COMMAND_COLUMNS = ['command_id', 'command_type', 'status', 'updated_at'] as const;

const EVENT_COLUMNS = ['event_id', 'event_type', 'occurred_at'] as const;

const RECEIPT_COLUMNS = ['receipt_id', 'signal_id', 'channel', 'result', 'attempted_at'] as const;

const SUPPRESSION_COLUMNS = ['signal_id', 'acknowledged_at', 'acknowledged_by'] as const;

function tableSpec(
  id: string,
  label: string,
  table: DataTableSnapshot | undefined,
  columns: readonly string[],
): DataSurfaceTableSpec {
  const items = table?.items ?? [];
  return {
    id,
    label,
    total: table?.total ?? 0,
    count: table?.count ?? items.length,
    columns: [...columns],
    rows: items.map((item) => {
      const row: Record<string, unknown> = {};
      for (const column of columns) {
        row[column] = item[column] ?? '';
      }
      return row;
    }),
  };
}

export function buildDataSurfaceTables(snapshot: OperatorDataSnapshot | null): DataSurfaceTableSpec[] {
  if (!snapshot) {
    return [];
  }

  return [
    tableSpec('runs', 'Runs', snapshot.control_plane.runs, RUN_COLUMNS),
    tableSpec('chat_threads', 'Chat threads', snapshot.control_plane.chat_threads, THREAD_COLUMNS),
    tableSpec('chat_messages', 'Chat messages', snapshot.control_plane.chat_messages, MESSAGE_COLUMNS),
    tableSpec('handoffs', 'Handoffs', snapshot.control_plane.handoffs, HANDOFF_COLUMNS),
    tableSpec('commands', 'Watch commands', snapshot.watch.commands, COMMAND_COLUMNS),
    tableSpec('events', 'Watch events', snapshot.watch.events, EVENT_COLUMNS),
    tableSpec('receipts', 'Delivery receipts', snapshot.watch.receipts, RECEIPT_COLUMNS),
    tableSpec('suppressions', 'Signal suppressions', snapshot.watch.suppressions, SUPPRESSION_COLUMNS),
  ];
}

export function dataSurfaceTotalRows(tables: DataSurfaceTableSpec[]): number {
  return tables.reduce((sum, table) => sum + table.total, 0);
}

export function formatDataCell(value: unknown): string {
  if (value === null || value === undefined || value === '') {
    return '—';
  }
  if (typeof value === 'object') {
    return JSON.stringify(value);
  }
  return String(value);
}

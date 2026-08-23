export type AgentEditOperation = 'created' | 'edited' | 'deleted' | 'touched' | 'changed';

export function agentEditOperation(input: {
  added: number;
  removed: number;
  diff?: string | null;
}): AgentEditOperation {
  const diff = String(input.diff ?? '').replace(/\r\n/g, '\n');
  if (/^(?:deleted file mode|\+\+\+ \/dev\/null\b)/m.test(diff)) {
    return 'deleted';
  }
  if (/^(?:new file mode|--- \/dev\/null\b)/m.test(diff)) {
    return 'created';
  }
  if (/^@@\s+-0,0\s+\+\d+(?:,\d+)?\s+@@/m.test(diff)) {
    return 'created';
  }
  if (/^@@\s+-\d+(?:,\d+)?\s+\+0,0\s+@@/m.test(diff)) {
    return 'deleted';
  }
  if (input.added <= 0 && input.removed <= 0) {
    return 'touched';
  }
  if (!diff.trim()) {
    return input.added > 0 && input.removed > 0 ? 'edited' : 'changed';
  }
  return 'edited';
}

export function agentEditOperationLabel(operation: AgentEditOperation): string {
  if (operation === 'created') {
    return 'Created file';
  }
  if (operation === 'deleted') {
    return 'Deleted file';
  }
  if (operation === 'touched') {
    return 'Checked file';
  }
  if (operation === 'changed') {
    return 'File change';
  }
  return 'Edited file';
}

export function agentEditEventLabel(input: {
  path: string;
  added: number;
  removed: number;
  diff?: string | null;
}): string {
  return `${agentEditOperationLabel(agentEditOperation(input))}: ${input.path}`;
}

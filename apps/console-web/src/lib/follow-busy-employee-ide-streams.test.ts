import { describe, expect, it } from 'vitest';

import type { CompanyEmployeeRecord } from '../contracts/canonical';
import {
  decideBusyEmployeeStreamAttach,
  findIdeThreadIdForEmployee,
  listBusyEmployeeStreamTargets,
  resolveStreamingAgentMessageId,
} from './follow-busy-employee-ide-streams';

function employee(partial: Partial<CompanyEmployeeRecord> & Pick<CompanyEmployeeRecord, 'employee_id' | 'name' | 'role'>): CompanyEmployeeRecord {
  return {
    enabled: true,
    status: 'executing',
    ...partial,
  } as CompanyEmployeeRecord;
}

describe('listBusyEmployeeStreamTargets', () => {
  it('includes mid-shift specialists and watchers with active_run_id', () => {
    const targets = listBusyEmployeeStreamTargets([
      employee({
        employee_id: 'emp-marco',
        name: 'Marco',
        role: 'backend',
        active_run_id: 'run_marco',
        status: 'executing',
      }),
      employee({
        employee_id: 'emp-cass',
        name: 'Cass',
        role: 'watcher',
        active_run_id: 'run_cass',
        status: 'watching',
      }),
      employee({
        employee_id: 'emp-soren',
        name: 'Soren',
        role: 'integrations',
        active_run_id: 'run_queued',
        status: 'assigned',
      }),
      employee({
        employee_id: 'emp-idle',
        name: 'Idle',
        role: 'frontend',
        active_run_id: 'run_stale',
        status: 'idle',
      }),
    ]);
    expect(targets).toEqual([
      { employeeId: 'emp-marco', runId: 'run_marco', name: 'Marco' },
      { employeeId: 'emp-cass', runId: 'run_cass', name: 'Cass' },
    ]);
  });
});

describe('resolveStreamingAgentMessageId', () => {
  it('picks the latest agent message for the run', () => {
    const messageId = resolveStreamingAgentMessageId(
      [
        { role: 'operator', run_id: 'run_a', message_id: 'op1' },
        { role: 'agent', run_id: 'run_a', message_id: 'ag1' },
        { role: 'agent', run_id: 'run_b', message_id: 'ag2' },
        { role: 'agent', run_id: 'run_a', message_id: 'ag3' },
      ],
      'run_a',
    );
    expect(messageId).toBe('ag3');
  });
});

describe('decideBusyEmployeeStreamAttach', () => {
  it('skips when thread or message is missing', () => {
    expect(
      decideBusyEmployeeStreamAttach({
        threadId: null,
        resolvedMessageId: 'm1',
        alreadyActive: false,
        alreadyMessageId: null,
      }),
    ).toBe('skip_no_thread');
    expect(
      decideBusyEmployeeStreamAttach({
        threadId: 'thread_1',
        resolvedMessageId: null,
        alreadyActive: false,
        alreadyMessageId: null,
      }),
    ).toBe('skip_no_message');
  });

  it('skips when the same stream is already attached', () => {
    expect(
      decideBusyEmployeeStreamAttach({
        threadId: 'thread_1',
        resolvedMessageId: 'm1',
        alreadyActive: true,
        alreadyMessageId: 'm1',
        hasLiveSession: true,
      }),
    ).toBe('skip_already');
  });

  it('reattaches when chrome is active but the EventSource is gone', () => {
    expect(
      decideBusyEmployeeStreamAttach({
        threadId: 'thread_1',
        resolvedMessageId: 'm1',
        alreadyActive: true,
        alreadyMessageId: 'm1',
        hasLiveSession: false,
      }),
    ).toBe('attach');
  });

  it('attaches when a new message id is ready', () => {
    expect(
      decideBusyEmployeeStreamAttach({
        threadId: 'thread_1',
        resolvedMessageId: 'm2',
        alreadyActive: true,
        alreadyMessageId: 'm1',
      }),
    ).toBe('attach');
  });
});

describe('findIdeThreadIdForEmployee', () => {
  it('matches by employee_id', () => {
    expect(
      findIdeThreadIdForEmployee(
        [
          { thread_id: 'thread_dana', employee_id: 'emp-dana' },
          { thread_id: 'thread_marco', employee_id: 'emp-marco' },
        ],
        'emp-marco',
      ),
    ).toBe('thread_marco');
  });
});

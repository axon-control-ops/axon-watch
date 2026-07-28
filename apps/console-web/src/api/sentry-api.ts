import { apiUrl, postJson } from './client';

export type SentryResolveResult = {
  ok: boolean;
  issue_id?: string;
  status?: string;
  reason?: string;
  detail?: string;
  requested_by?: string;
  write_scope?: boolean;
  status_code?: number;
};

export type SentryWriteProbeResult = {
  ok: boolean;
  write_scope?: boolean;
  reason?: string;
  detail?: string;
  status_code?: number;
};

function errorMessageFromPayload(payload: unknown, fallback: string): string {
  if (!payload || typeof payload !== 'object') {
    return fallback;
  }
  const record = payload as Record<string, unknown>;
  const detail = record.detail;
  if (typeof detail === 'string' && detail.trim()) {
    return detail.trim();
  }
  if (detail && typeof detail === 'object') {
    const nested = detail as Record<string, unknown>;
    if (typeof nested.detail === 'string' && nested.detail.trim()) {
      return nested.detail.trim();
    }
    if (typeof nested.reason === 'string' && nested.reason.trim()) {
      return nested.reason.trim();
    }
  }
  if (typeof record.reason === 'string' && record.reason.trim()) {
    return record.reason.trim();
  }
  return fallback;
}

export type SentryAttendResult = {
  ok: boolean;
  issue_id?: string;
  detail?: string;
  reason?: string;
  attendance?: {
    issue_id: string;
    confirm_release: string;
    attended_at: string;
  };
  sentry?: SentryResolveResult | null;
};

export async function resolveSentryIssue(
  issueId: string,
  body: { status?: string; requested_by?: string } = {},
): Promise<SentryResolveResult> {
  const normalized = String(issueId || '').trim();
  if (!normalized) {
    return { ok: false, reason: 'missing_issue_id' };
  }

  const response = await fetch(apiUrl(`/api/sentry/issues/${encodeURIComponent(normalized)}/resolve`), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      status: body.status ?? 'resolved',
      requested_by: body.requested_by ?? 'operator',
    }),
  });

  let payload: unknown = null;
  try {
    payload = await response.json();
  } catch {
    payload = null;
  }

  if (!response.ok) {
    const detailPayload =
      payload && typeof payload === 'object' && 'detail' in (payload as object)
        ? (payload as { detail: unknown }).detail
        : payload;
    if (detailPayload && typeof detailPayload === 'object') {
      return detailPayload as SentryResolveResult;
    }
    throw new Error(errorMessageFromPayload(payload, `sentry resolve failed (${response.status})`));
  }

  return (payload ?? { ok: true, issue_id: normalized }) as SentryResolveResult;
}

export async function attendSentryIssue(
  issueId: string,
  body: {
    confirm_release?: string;
    requested_by?: string;
    mark_resolved_in_next_release?: boolean;
    workspace_id?: string;
  } = {},
): Promise<SentryAttendResult> {
  const normalized = String(issueId || '').trim();
  if (!normalized) {
    return { ok: false, reason: 'missing_issue_id' };
  }

  const response = await fetch(apiUrl(`/api/sentry/issues/${encodeURIComponent(normalized)}/attend`), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      confirm_release: body.confirm_release ?? '',
      requested_by: body.requested_by ?? 'operator',
      mark_resolved_in_next_release: body.mark_resolved_in_next_release ?? true,
      workspace_id: body.workspace_id ?? 'workspace_dashpro',
    }),
  });

  let payload: unknown = null;
  try {
    payload = await response.json();
  } catch {
    payload = null;
  }

  if (!response.ok) {
    const detailPayload =
      payload && typeof payload === 'object' && 'detail' in (payload as object)
        ? (payload as { detail: unknown }).detail
        : payload;
    if (detailPayload && typeof detailPayload === 'object') {
      return detailPayload as SentryAttendResult;
    }
    throw new Error(errorMessageFromPayload(payload, `sentry attend failed (${response.status})`));
  }

  return (payload ?? { ok: true, issue_id: normalized }) as SentryAttendResult;
}

export async function probeSentryWriteScope(): Promise<SentryWriteProbeResult> {
  return postJson<SentryWriteProbeResult>('/api/sentry/probe-write', {}, 'sentry write probe failed');
}

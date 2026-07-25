function controlPlaneBaseUrl(): string {
  const configured = import.meta.env.VITE_CONTROL_PLANE_BASE_URL;
  if (configured) {
    return configured.replace(/\/$/, '');
  }

  if (import.meta.env.DEV) {
    return 'http://127.0.0.1:8787';
  }

  return '';
}

export function buildTerminalWebSocketUrl(
  workspaceId: string,
  options: {
    baseUrl?: string;
    sessionId?: string;
    role?: string;
  } = {},
): string {
  const encodedWorkspaceId = encodeURIComponent(workspaceId);
  const sessionId = encodeURIComponent(options.sessionId ?? 'terminal-operator');
  const role = encodeURIComponent(options.role ?? 'operator');
  const query = `?session_id=${sessionId}&role=${role}`;
  const httpBase = (options.baseUrl ?? controlPlaneBaseUrl()).replace(/\/$/, '');

  if (httpBase) {
    const wsBase = httpBase.replace(/^http/i, 'ws');
    return `${wsBase}/api/workspaces/${encodedWorkspaceId}/terminal${query}`;
  }

  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${protocol}//${window.location.host}/api/workspaces/${encodedWorkspaceId}/terminal${query}`;
}

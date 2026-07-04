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

export function buildTerminalWebSocketUrl(workspaceId: string, baseUrl?: string): string {
  const encodedWorkspaceId = encodeURIComponent(workspaceId);
  const httpBase = (baseUrl ?? controlPlaneBaseUrl()).replace(/\/$/, '');

  if (httpBase) {
    const wsBase = httpBase.replace(/^http/i, 'ws');
    return `${wsBase}/api/workspaces/${encodedWorkspaceId}/terminal`;
  }

  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${protocol}//${window.location.host}/api/workspaces/${encodedWorkspaceId}/terminal`;
}

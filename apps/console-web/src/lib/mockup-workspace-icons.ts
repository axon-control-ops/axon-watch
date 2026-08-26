export function workspaceIconKind(workspaceId: string): string {
  if (workspaceId.includes('axon_watch') || workspaceId.includes('watch')) {
    return 'cube';
  }
  if (workspaceId.includes('dashpro') || workspaceId.includes('dash_pro')) {
    return 'building';
  }
  if (workspaceId.includes('tps') || workspaceId.includes('young_eagles')) {
    return 'building';
  }
  if (workspaceId.includes('smoke')) {
    return 'cube';
  }
  if (workspaceId.includes('recsys')) {
    return 'cube';
  }
  if (workspaceId.includes('finance')) {
    return 'building';
  }
  if (workspaceId.includes('nlp')) {
    return 'chat';
  }
  if (workspaceId.includes('cv')) {
    return 'lens';
  }
  if (workspaceId.includes('edge')) {
    return 'tower';
  }
  if (workspaceId.includes('research')) {
    return 'flask';
  }
  if (workspaceId.includes('bootstrap')) {
    return 'orbit';
  }
  if (workspaceId.includes('alpha')) {
    return 'hex';
  }
  return 'hex';
}

/** @deprecated Use `workspaceIconKind()` + CSS glyphs. */
export function workspaceIcon(workspaceId: string): string {
  if (workspaceId.includes('smoke')) {
    return '⧉';
  }
  if (workspaceId.includes('recsys')) {
    return '▣';
  }
  if (workspaceId.includes('finance')) {
    return '⛫';
  }
  if (workspaceId.includes('nlp')) {
    return '◎';
  }
  if (workspaceId.includes('cv')) {
    return '◉';
  }
  if (workspaceId.includes('edge')) {
    return '△';
  }
  if (workspaceId.includes('research')) {
    return '⚗';
  }
  if (workspaceId.includes('bootstrap')) {
    return '◎';
  }
  if (workspaceId.includes('alpha')) {
    return '⬡';
  }
  return '⬡';
}

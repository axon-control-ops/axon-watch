export function researchHostname(url: string): string {
  const trimmed = url.trim();
  if (!trimmed) {
    return '';
  }
  try {
    return new URL(trimmed).hostname.replace(/^www\./, '');
  } catch {
    return trimmed;
  }
}

export function researchFaviconUrl(url: string): string | null {
  const hostname = researchHostname(url);
  if (!hostname || hostname === 'about:blank') {
    return null;
  }
  return `https://www.google.com/s2/favicons?domain=${encodeURIComponent(hostname)}&sz=32`;
}

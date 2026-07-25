function parseJsonObject(value: string): Record<string, unknown> | null {
  const trimmed = value.trim();
  if (!trimmed.startsWith('{')) {
    return null;
  }
  try {
    const parsed = JSON.parse(trimmed) as unknown;
    return parsed && typeof parsed === 'object' ? (parsed as Record<string, unknown>) : null;
  } catch {
    return null;
  }
}

export function sanitizeResearchSnippet(snippet: string): string {
  const cleaned = snippet.trim();
  if (!cleaned) {
    return '';
  }

  const direct = parseJsonObject(cleaned);
  if (direct) {
    if (direct.success === false) {
      return String(direct.error ?? 'Research request failed').slice(0, 500);
    }
    const content = String(direct.content ?? '').trim();
    if (content) {
      return content.slice(0, 500);
    }
    const results = direct.results;
    if (Array.isArray(results)) {
      if (results.length === 0) {
        return String(direct.query ?? 'No web results').slice(0, 500);
      }
      const first = results[0];
      if (first && typeof first === 'object') {
        const record = first as Record<string, unknown>;
        return String(record.snippet ?? record.description ?? record.title ?? '').slice(0, 500);
      }
    }
  }

  const envelopeMatch = cleaned.match(/['"]text['"]\s*:\s*['"](\{.*\})['"]/s);
  if (envelopeMatch?.[1]) {
    const nested = parseJsonObject(envelopeMatch[1].replace(/\\n/g, '\n').replace(/\\"/g, '"'));
    if (nested) {
      return sanitizeResearchSnippet(JSON.stringify(nested));
    }
  }

  if (cleaned.startsWith("[{'text'") || cleaned.startsWith('[{"text"')) {
    const queryMatch = cleaned.match(/"query":\s*"([^"]+)"/);
    if (queryMatch?.[1] && cleaned.includes('"results": []')) {
      return queryMatch[1];
    }
    const errorMatch = cleaned.match(/"error":\s*"([^"]+)"/);
    if (errorMatch?.[1]) {
      return errorMatch[1];
    }
  }

  if (cleaned.startsWith('[{') && cleaned.includes('"success"')) {
    const queryMatch = cleaned.match(/"query":\s*"([^"]+)"/);
    if (queryMatch?.[1] && cleaned.includes('"results": []')) {
      return queryMatch[1];
    }
    const errorMatch = cleaned.match(/"error":\s*"([^"]+)"/);
    if (errorMatch?.[1]) {
      return errorMatch[1];
    }
  }

  return cleaned.slice(0, 500);
}

export function sanitizeResearchCardTitle(title: string, snippet: string, url: string): string {
  const normalizedTitle = title.trim();
  if (normalizedTitle && normalizedTitle !== 'Fetched page') {
    return normalizedTitle;
  }
  if (snippet.startsWith('HTTP ')) {
    return 'Fetch failed';
  }
  if (snippet && !snippet.startsWith('[{') && !snippet.startsWith('{')) {
    return normalizedTitle || 'Research result';
  }
  return normalizedTitle || 'Research result';
}

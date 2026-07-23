/** Clean plan markdown for editor preview (defense in depth vs capture). */

const NOISY_FENCE_RE =
  /^:::(?:thinking|research|tool|ask|plan)\b[\s\S]*?(?:^:::\s*$|(?![\s\S]))/gm;
const PROCESS_LINE_RE =
  /^(i'?ll|i will|i am|i'?m|let me|looking|gathering|drafting|searching|checking|reading|i have enough|the request is|axon research is ready|research is ready|next i'?ll|next i will)\b/i;

export function sanitizePlanMarkdownForDisplay(content: string): string {
  let text = String(content ?? '').replace(NOISY_FENCE_RE, '');
  text = text.replace(/\n{3,}/g, '\n\n').trim();
  if (!text) {
    return '';
  }

  const lines = text.split('\n');
  const out: string[] = [];
  let index = 0;
  let openingHeading = '';
  if (lines[0] && /^#{1,3}\s+\S/.test(lines[0].trim())) {
    out.push(lines[0]);
    openingHeading = lines[0].trim();
    index = 1;
    while (index < lines.length && !lines[index]?.trim()) {
      index += 1;
    }
  }

  while (index < lines.length) {
    const raw = lines[index] ?? '';
    const stripped = raw.trim();
    if (!stripped) {
      index += 1;
      continue;
    }
    if (openingHeading && stripped === openingHeading) {
      index += 1;
      while (index < lines.length && !lines[index]?.trim()) {
        index += 1;
      }
      continue;
    }
    if (stripped.startsWith('##')) {
      break;
    }
    if (/^\d+[\.\)]\s+\S/.test(stripped) || /^-\s+\[[ xX]\]\s+\S/.test(stripped)) {
      break;
    }
    if (PROCESS_LINE_RE.test(stripped)) {
      index += 1;
      while (index < lines.length && !lines[index]?.trim()) {
        index += 1;
      }
      continue;
    }
    break;
  }

  const rest = lines.slice(index);
  if (out.length > 0 && rest.length > 0 && (rest[0] ?? '').trim()) {
    out.push('');
  }
  out.push(...rest);
  return out.join('\n').trim();
}

const EDITOR_LANGUAGE_LABELS: Record<string, string> = {
  markdown: 'Markdown',
  json: 'JSON',
  plaintext: 'Plain Text',
  typescript: 'TypeScript',
  javascript: 'JavaScript',
  python: 'Python',
  shell: 'Shell',
  html: 'HTML',
  css: 'CSS',
  csv: 'CSV',
  image: 'Image',
  yaml: 'YAML',
  toml: 'TOML',
  sql: 'SQL',
  xml: 'XML',
  rust: 'Rust',
  go: 'Go',
  ini: 'Ini',
  graphql: 'GraphQL',
  dockerfile: 'Dockerfile',
};

function pathLanguageLabel(filePath: string | null | undefined): string | null {
  const path = (filePath ?? '').trim().toLowerCase();
  if (!path) {
    return null;
  }

  if (path.endsWith('.tsx')) {
    return 'TSX';
  }
  if (path.endsWith('.jsx')) {
    return 'JSX';
  }
  if (path.endsWith('.mdx')) {
    return 'MDX';
  }
  if (path.endsWith('.vue')) {
    return 'Vue';
  }
  if (/\.ya?ml$/.test(path)) {
    return 'YAML';
  }
  if (path.endsWith('.toml')) {
    return 'TOML';
  }
  if (path.endsWith('.scss')) {
    return 'SCSS';
  }
  if (path.endsWith('.sql')) {
    return 'SQL';
  }
  if (path.endsWith('.csv')) {
    return 'CSV';
  }
  if (path.endsWith('.tsv')) {
    return 'TSV';
  }

  return null;
}

/** Human-readable language label for the IDE editor status bar. */
export function buildEditorLanguageLabel(input: {
  language: string;
  filePath?: string | null;
  isAgentEditReview: boolean;
  isMarkdownEditorDocument: boolean;
}): string {
  if (input.isAgentEditReview && !input.isMarkdownEditorDocument) {
    return 'Diff review';
  }
  if (input.isAgentEditReview && input.isMarkdownEditorDocument) {
    return 'Markdown review';
  }

  const pathLabel = pathLanguageLabel(input.filePath);
  if (pathLabel) {
    return pathLabel;
  }

  return EDITOR_LANGUAGE_LABELS[input.language] ?? input.language;
}

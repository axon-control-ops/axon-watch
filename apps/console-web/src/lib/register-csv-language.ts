import type * as Monaco from 'monaco-editor';

const CSV_LANGUAGE_ID = 'csv';

let registered = false;

export function registerCsvLanguage(monaco: typeof Monaco): void {
  if (registered) {
    return;
  }
  registered = true;

  monaco.languages.register({ id: CSV_LANGUAGE_ID });

  monaco.languages.setMonarchTokensProvider(CSV_LANGUAGE_ID, {
    defaultToken: 'source',
    tokenizer: {
      root: [
        [/"/, 'string.csv', '@csvString'],
        [/\t/, 'delimiter.csv'],
        [/,/, 'delimiter.csv'],
        [/;/, 'delimiter.csv'],
        [/\|/, 'delimiter.csv'],
        [/-?\d+(?:\.\d+)?/, 'number.csv'],
        [/[^\t",;|]+/, 'source'],
      ],
      csvString: [
        [/""/, 'string.csv'],
        [/"/, 'string.csv', '@pop'],
        [/./, 'string.csv'],
      ],
    },
  });
}

export { CSV_LANGUAGE_ID };

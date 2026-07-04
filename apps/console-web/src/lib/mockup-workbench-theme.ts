import type * as Monaco from 'monaco-editor';
import type { ITheme } from '@xterm/xterm';

export const MOCKUP_WORKBENCH_FONT =
  'JetBrains Mono, ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace';

export const MOCKUP_EDITOR_SURFACE = '#05111b';
export const MOCKUP_TERMINAL_SURFACE = '#061424';
export const MOCKUP_WORKBENCH_CHROME = '#031622';

export const MOCKUP_MONACO_THEME_ID = 'axon-watch-mockup';

const editorRules: Monaco.editor.ITokenThemeRule[] = [
  { token: 'comment', foreground: '5a7a94', fontStyle: 'italic' },
  { token: 'keyword', foreground: '00f2ff' },
  { token: 'string', foreground: 'e8f4fc' },
  { token: 'number', foreground: '8ec8e8' },
  { token: 'type', foreground: '7ec8e0' },
  { token: 'markup.heading', foreground: '00f2ff', fontStyle: 'bold' },
  { token: 'markup.bold', foreground: '00f2ff', fontStyle: 'bold' },
  { token: 'markup.italic', foreground: 'c8dce8', fontStyle: 'italic' },
  { token: 'markup.inline.raw', foreground: '00f2ff' },
  { token: 'markup.fenced_code', foreground: '00f2ff' },
  { token: 'string.other.link.title.markdown', foreground: '00f2ff' },
  { token: 'variable', foreground: 'd8e8f4' },
  { token: 'identifier', foreground: 'd8e8f4' },
];

const editorColors: Monaco.editor.IColors = {
  'editor.background': MOCKUP_EDITOR_SURFACE,
  'editor.foreground': '#d8e8f4',
  'editorLineNumber.foreground': '#4a6880',
  'editorLineNumber.activeForeground': '#7eb0cc',
  'editor.lineHighlightBackground': '#061828',
  'editor.selectionBackground': '#103044',
  'editor.inactiveSelectionBackground': '#0c2838',
  'editorCursor.foreground': '#00f2ff',
  'editorWhitespace.foreground': '#1a3040',
  'editorIndentGuide.background': '#122838',
  'editorIndentGuide.activeBackground': '#1e4460',
};

export function defineMockupMonacoTheme(monaco: typeof Monaco): void {
  monaco.editor.defineTheme(MOCKUP_MONACO_THEME_ID, {
    base: 'vs-dark',
    inherit: true,
    rules: editorRules,
    colors: editorColors,
  });
}

export const mockupXtermTheme: ITheme = {
  background: MOCKUP_TERMINAL_SURFACE,
  foreground: '#d4e4f0',
  cursor: '#00f2ff',
  black: '#05111b',
  red: '#ff6b4a',
  green: '#8fd9b2',
  yellow: '#e8c878',
  blue: '#6eb8d8',
  magenta: '#c8a0d8',
  cyan: '#00f2ff',
  white: '#d4e4f0',
  brightBlack: '#7a94a8',
  brightRed: '#ff8a72',
  brightGreen: '#9ef0c3',
  brightYellow: '#f0d898',
  brightBlue: '#9ec8e8',
  brightMagenta: '#ddb8f0',
  brightCyan: '#66f6ff',
  brightWhite: '#f2f8fc',
};

export const mockupEditorFontOptions = {
  fontSize: 14,
  lineHeight: 20,
  fontFamily: MOCKUP_WORKBENCH_FONT,
  fontLigatures: false,
};

export const mockupTerminalFontOptions = {
  fontSize: 14,
  lineHeight: 1.3,
  fontFamily: MOCKUP_WORKBENCH_FONT,
};

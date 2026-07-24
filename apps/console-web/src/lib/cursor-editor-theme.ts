import type * as Monaco from 'monaco-editor';

/** Cursor / VS Code Dark+ aligned editor palette. */
export const CURSOR_EDITOR_SURFACE = '#1e1e1e';
export const CURSOR_MONACO_THEME_ID = 'axon-cursor-dark';

const editorRules: Monaco.editor.ITokenThemeRule[] = [
  { token: '', foreground: 'd4d4d4' },
  { token: 'comment', foreground: '6a9955', fontStyle: 'italic' },
  { token: 'keyword', foreground: '569cd6' },
  { token: 'string', foreground: 'ce9178' },
  { token: 'number', foreground: 'b5cea8' },
  { token: 'regexp', foreground: 'd16969' },
  { token: 'type', foreground: '4ec9b0' },
  { token: 'class', foreground: '4ec9b0' },
  { token: 'interface', foreground: '4ec9b0' },
  { token: 'function', foreground: 'dcdcaa' },
  { token: 'variable', foreground: '9cdcfe' },
  { token: 'variable.predefined', foreground: '4fc1ff' },
  { token: 'delimiter', foreground: 'd4d4d4' },
  { token: 'delimiter.csv', foreground: '808080' },
  { token: 'string.csv', foreground: 'ce9178' },
  { token: 'number.csv', foreground: 'b5cea8' },
  { token: 'markup.heading', foreground: '569cd6', fontStyle: 'bold' },
  { token: 'markup.bold', foreground: '569cd6', fontStyle: 'bold' },
  { token: 'markup.italic', foreground: 'c586c0', fontStyle: 'italic' },
  { token: 'markup.inline.raw', foreground: 'ce9178' },
  { token: 'markup.fenced_code', foreground: 'ce9178' },
];

const editorColors: Monaco.editor.IColors = {
  'editor.background': CURSOR_EDITOR_SURFACE,
  'editor.foreground': '#d4d4d4',
  'editorLineNumber.foreground': '#858585',
  'editorLineNumber.activeForeground': '#c6c6c6',
  'editor.lineHighlightBackground': '#2a2d2e',
  'editor.selectionBackground': '#264f78',
  'editor.inactiveSelectionBackground': '#3a3d41',
  'editorCursor.foreground': '#aeafad',
  'editorWhitespace.foreground': '#3b3b3b',
  'editorIndentGuide.background': '#404040',
  'editorIndentGuide.activeBackground': '#707070',
  'editorBracketHighlight.foreground1': '#ffd700',
  'editorBracketHighlight.foreground2': '#da70d6',
  'editorBracketHighlight.foreground3': '#179fff',
  'editorBracketMatch.border': '#888888',
  'editorBracketMatch.background': '#0064001a',
  'editorOverviewRuler.border': '#00000000',
  'minimap.background': '#1e1e1e',
  'minimapSlider.background': '#79797933',
  'minimapSlider.hoverBackground': '#64646459',
  'minimapSlider.activeBackground': '#bfbfbf66',
  'editorStickyScroll.background': '#252526',
  'editorStickyScrollHover.background': '#2a2d2e',
  'editorGutter.foldingControlForeground': '#c5c5c5',
};

export const cursorEditorFontOptions = {
  fontSize: 14,
  lineHeight: 21,
  fontFamily: "'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
  fontLigatures: true,
};

/** VS Code / Cursor minimap — scale 1, rendered glyphs, narrow gutter. */
export const cursorMinimapOptions = {
  scale: 1 as const,
  showSlider: 'mouseover' as const,
  renderCharacters: true,
  maxColumn: 120,
  size: 'proportional' as const,
  side: 'right' as const,
};

/** Operator HUD minimap — slightly wider blocks, still single-scale. */
export const mockupMinimapOptions = {
  scale: 1 as const,
  showSlider: 'mouseover' as const,
  renderCharacters: true,
  maxColumn: 80,
  size: 'proportional' as const,
  side: 'right' as const,
};

export function defineCursorMonacoTheme(monaco: typeof Monaco): void {
  monaco.editor.defineTheme(CURSOR_MONACO_THEME_ID, {
    base: 'vs-dark',
    inherit: true,
    rules: editorRules,
    colors: editorColors,
  });
}

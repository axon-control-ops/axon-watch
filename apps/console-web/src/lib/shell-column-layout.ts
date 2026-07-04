export function parseCssLengthPx(value: string, remPx = 16): number {
  const trimmed = value.trim();
  if (!trimmed) {
    return 0;
  }

  if (trimmed.endsWith('px')) {
    const px = parseFloat(trimmed);
    return Number.isFinite(px) && px > 0 ? px : 0;
  }

  if (trimmed.endsWith('rem')) {
    const rem = parseFloat(trimmed);
    return Number.isFinite(rem) && rem > 0 ? rem * remPx : 0;
  }

  const numeric = parseFloat(trimmed);
  return Number.isFinite(numeric) && numeric > 0 ? numeric : 0;
}

export function readShellFooterGapPx(shell: Element | null): number {
  if (!shell) {
    return 0;
  }

  const styles = getComputedStyle(shell);
  const rowGap = parseFloat(styles.rowGap);
  if (Number.isFinite(rowGap) && rowGap > 0) {
    return rowGap;
  }

  const column = shell.querySelector('.region-center-workbench, .region-left-sidebar');
  if (column) {
    const marginBottom = parseFloat(getComputedStyle(column).marginBottom);
    if (Number.isFinite(marginBottom) && marginBottom > 0) {
      return marginBottom;
    }
  }

  const statusBar = shell.querySelector('.region-status-bar');
  if (statusBar) {
    const marginTop = parseFloat(getComputedStyle(statusBar).marginTop);
    if (Number.isFinite(marginTop) && marginTop > 0) {
      return marginTop;
    }
  }

  const rootFontSize = parseFloat(getComputedStyle(document.documentElement).fontSize) || 16;
  const gutter = parseCssLengthPx(styles.getPropertyValue('--shell-gutter'), rootFontSize);
  return gutter > 0 ? gutter : 0;
}

export function computeShellColumnMinHeight(
  columnTop: number,
  statusBarTop: number,
  footerGapPx: number,
): number {
  return Math.max(0, statusBarTop - footerGapPx - columnTop);
}

export function isShellLayoutGeometrySane(
  columnTop: number,
  statusBarTop: number,
  viewportHeight = typeof window === 'undefined' ? 900 : window.innerHeight,
): boolean {
  if (!Number.isFinite(columnTop) || !Number.isFinite(statusBarTop)) {
    return false;
  }

  if (columnTop < 0 || statusBarTop < 0) {
    return false;
  }

  if (columnTop > viewportHeight * 1.25 || statusBarTop > viewportHeight * 1.25) {
    return false;
  }

  return statusBarTop > columnTop;
}

/** Operator hero is a fixed compact command strip, not terminal-coupled. */
export const OPERATOR_HERO_DOCK_HEIGHT_PX = 188;

/** IDE hero scales with terminal dock but stays capped. */
export const IDE_HERO_DOCK_HEIGHT_RATIO = 0.42;
export const MIN_IDE_HERO_DOCK_HEIGHT_PX = 128;
export const MAX_IDE_HERO_DOCK_HEIGHT_PX = 176;

export type ShellLayoutMode = 'operator' | 'ide';

export function computeHeroDockHeight(
  terminalDockHeightPx: number,
  layoutMode: ShellLayoutMode = 'operator',
): number {
  if (layoutMode === 'operator') {
    return OPERATOR_HERO_DOCK_HEIGHT_PX;
  }

  if (!Number.isFinite(terminalDockHeightPx) || terminalDockHeightPx <= 0) {
    return MIN_IDE_HERO_DOCK_HEIGHT_PX;
  }

  return Math.min(
    MAX_IDE_HERO_DOCK_HEIGHT_PX,
    Math.max(
      MIN_IDE_HERO_DOCK_HEIGHT_PX,
      Math.round(terminalDockHeightPx * IDE_HERO_DOCK_HEIGHT_RATIO),
    ),
  );
}

/** @deprecated Use computeHeroDockHeight. */
export function computeBriefingDockHeight(terminalDockHeightPx: number): number {
  return computeHeroDockHeight(terminalDockHeightPx, 'ide');
}

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

/** Briefing seam tracks terminal dock height but stays slightly shorter. */
export const BRIEFING_DOCK_HEIGHT_RATIO = 0.82;
export const MIN_BRIEFING_DOCK_HEIGHT_PX = 152;

export function computeBriefingDockHeight(terminalDockHeightPx: number): number {
  if (!Number.isFinite(terminalDockHeightPx) || terminalDockHeightPx <= 0) {
    return 0;
  }

  return Math.max(
    MIN_BRIEFING_DOCK_HEIGHT_PX,
    Math.round(terminalDockHeightPx * BRIEFING_DOCK_HEIGHT_RATIO),
  );
}

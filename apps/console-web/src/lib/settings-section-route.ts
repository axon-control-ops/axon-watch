import { appSurfacePath, normalizeAppPath } from './app-surface-route';

export type SettingsSection = 'voice' | 'agents' | 'runtime' | 'email' | 'app';

const SETTINGS_SECTIONS = new Set<SettingsSection>([
  'voice',
  'agents',
  'runtime',
  'email',
  'app',
]);

export const SETTINGS_SECTION_EVENT = 'axon-settings-section';

export function normalizeSettingsSection(
  value: string | null | undefined,
): SettingsSection | null {
  const trimmed = (value ?? '').trim().replace(/^#/, '').toLowerCase();
  if (!trimmed || !SETTINGS_SECTIONS.has(trimmed as SettingsSection)) {
    return null;
  }
  return trimmed as SettingsSection;
}

export function readSettingsSectionHash(
  location: Pick<Location, 'hash'> = window.location,
): SettingsSection | null {
  return normalizeSettingsSection(location.hash);
}

export function writeSettingsSectionHash(section: SettingsSection, replace = true): void {
  const basePath = appSurfacePath('settings');
  const nextUrl = `${basePath}#${section}`;
  const currentUrl = `${normalizeAppPath(window.location.pathname)}${window.location.hash}`;
  if (currentUrl === nextUrl) {
    return;
  }
  if (replace) {
    window.history.replaceState({}, '', nextUrl);
  } else {
    window.history.pushState({}, '', nextUrl);
  }
}

export function navigateToSettingsSection(section: SettingsSection): void {
  const nextUrl = `${appSurfacePath('settings')}#${section}`;
  const onSettings = normalizeAppPath(window.location.pathname) === appSurfacePath('settings');
  if (!onSettings || `${window.location.pathname}${window.location.hash}` !== nextUrl) {
    window.history.pushState({}, '', nextUrl);
  }
  window.dispatchEvent(new Event('axon-app-surface'));
  window.dispatchEvent(new Event(SETTINGS_SECTION_EVENT));
}

export function isSettingsSection(value: string): value is SettingsSection {
  return SETTINGS_SECTIONS.has(value as SettingsSection);
}

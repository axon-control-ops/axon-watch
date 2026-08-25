import { Platform } from "react-native";

function isLocalControlPlane(url: string): boolean {
  return /^https?:\/\/(?:127\.0\.0\.1|localhost)(?::\d+)?$/i.test(url);
}

function browserOrigin(): string {
  const location = (globalThis as { location?: { origin?: string } }).location;
  return typeof location?.origin === "string" && location.origin.trim()
    ? location.origin
    : "the Expo web origin";
}

export function explainFetchFailure(message: string, controlPlaneUrl: string): string {
  const normalized = message.trim();
  if (
    Platform.OS === "web" &&
    normalized === "Failed to fetch" &&
    isLocalControlPlane(controlPlaneUrl)
  ) {
    return `Browser dev at ${browserOrigin()} cannot reach ${controlPlaneUrl} until the control plane allows that origin with CORS.`;
  }
  return normalized;
}

export function surfaceErrorHint(controlPlaneUrl: string, errorMessage: string): string {
  if (
    Platform.OS === "web" &&
    errorMessage.includes("allows that origin with CORS") &&
    isLocalControlPlane(controlPlaneUrl)
  ) {
    return `Allow ${browserOrigin()} in the control-plane CORS list for browser dev, or run against a reachable tunnel/proxy on a device.`;
  }
  return "Set EXPO_PUBLIC_AXON_CONTROL_PLANE_URL to a reachable host address when running on a physical phone. Use a read-only tunnel or proxy when auth is required.";
}

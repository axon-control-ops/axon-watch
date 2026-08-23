import { StatusBar } from "expo-status-bar";
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ActivityIndicator,
  Pressable,
  RefreshControl,
  SafeAreaView,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { explainFetchFailure, surfaceErrorHint } from "./fetch-hints";

const CONTROL_PLANE_URL = (
  process.env.EXPO_PUBLIC_AXON_CONTROL_PLANE_URL ?? "http://127.0.0.1:8787"
).replace(/\/$/, "");

const SURFACES = [
  { key: "health", label: "Health", path: "/api/health" },
  { key: "runtime", label: "Runtime", path: "/api/runtime/summary" },
  { key: "briefing", label: "Briefing", path: "/api/briefing" },
  { key: "runs", label: "Runs", path: "/api/runs" },
  { key: "inbox", label: "Inbox", path: "/api/inbox" },
] as const;

type SurfaceKey = (typeof SURFACES)[number]["key"];
type Snapshot = Partial<Record<SurfaceKey, unknown>>;
type Failures = Partial<Record<SurfaceKey, string>>;

function compactJson(value: unknown): string {
  if (value === undefined) return "No data returned.";
  return JSON.stringify(value, null, 2);
}

function summarizeSurface(value: unknown): string {
  if (!value || typeof value !== "object") return "No summary";
  const record = value as Record<string, unknown>;
  if (typeof record.status === "string") return record.status;
  if (typeof record.phase === "string") return record.phase;
  if (typeof record.count === "number") return `${record.count} items`;
  if (Array.isArray(record.items)) return `${record.items.length} items`;
  if (Array.isArray(record.runs)) return `${record.runs.length} runs`;
  return `${Object.keys(record).length} fields`;
}

export default function App() {
  const [active, setActive] = useState<SurfaceKey>("health");
  const [snapshot, setSnapshot] = useState<Snapshot>({});
  const [failures, setFailures] = useState<Failures>({});
  const [refreshing, setRefreshing] = useState(false);
  const [updatedAt, setUpdatedAt] = useState<Date | null>(null);

  const refresh = useCallback(async () => {
    setRefreshing(true);
    try {
      const results = await Promise.all(
        SURFACES.map(async (surface) => {
          try {
            const response = await fetch(`${CONTROL_PLANE_URL}${surface.path}`, {
              headers: { Accept: "application/json" },
            });
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            return { key: surface.key, data: await response.json() } as const;
          } catch (error) {
            const message = error instanceof Error ? error.message : "Request failed";
            return {
              key: surface.key,
              error: explainFetchFailure(message, CONTROL_PLANE_URL),
            } as const;
          }
        }),
      );

      const nextSnapshot: Snapshot = {};
      const nextFailures: Failures = {};
      for (const result of results) {
        if ("data" in result) nextSnapshot[result.key] = result.data;
        else nextFailures[result.key] = result.error;
      }
      setSnapshot(nextSnapshot);
      setFailures(nextFailures);
      setUpdatedAt(new Date());
    } finally {
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const selected = useMemo(
    () => SURFACES.find((surface) => surface.key === active) ?? SURFACES[0],
    [active],
  );
  const selectedError = failures[active];

  return (
    <SafeAreaView style={styles.safeArea}>
      <StatusBar style="light" />
      <ScrollView
        contentContainerStyle={styles.page}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={refresh} tintColor="#66e3c4" />
        }
      >
        <View style={styles.header}>
          <View>
            <Text style={styles.eyebrow}>AXON-X</Text>
            <Text style={styles.title}>Companion</Text>
          </View>
          <View style={styles.badge}>
            <Text style={styles.badgeText}>READ ONLY</Text>
          </View>
        </View>

        <Text style={styles.subtitle}>Mobile control-plane visibility without device mutations.</Text>
        <Text numberOfLines={1} style={styles.endpoint}>
          {CONTROL_PLANE_URL}
        </Text>

        <View style={styles.grid}>
          {SURFACES.map((surface) => {
            const isActive = surface.key === active;
            const hasError = Boolean(failures[surface.key]);
            return (
              <Pressable
                accessibilityRole="button"
                accessibilityState={{ selected: isActive }}
                key={surface.key}
                onPress={() => setActive(surface.key)}
                style={[styles.tile, isActive && styles.activeTile]}
              >
                <View style={[styles.dot, hasError ? styles.errorDot : styles.okDot]} />
                <Text style={[styles.tileLabel, isActive && styles.activeTileLabel]}>
                  {surface.label}
                </Text>
                <Text numberOfLines={1} style={styles.tileValue}>
                  {hasError ? "Unavailable" : summarizeSurface(snapshot[surface.key])}
                </Text>
              </Pressable>
            );
          })}
        </View>

        <View style={styles.panel}>
          <View style={styles.panelHeader}>
            <View>
              <Text style={styles.panelTitle}>{selected.label}</Text>
              <Text style={styles.path}>{selected.path}</Text>
            </View>
            {refreshing ? <ActivityIndicator color="#66e3c4" /> : null}
          </View>

          {selectedError ? (
            <View style={styles.errorPanel}>
              <Text style={styles.errorTitle}>Unavailable</Text>
              <Text style={styles.errorText}>{selectedError}</Text>
              <Text style={styles.errorHint}>
                {surfaceErrorHint(CONTROL_PLANE_URL, selectedError)}
              </Text>
            </View>
          ) : (
            <ScrollView horizontal style={styles.payloadScroller}>
              <Text selectable style={styles.payload}>
                {compactJson(snapshot[active])}
              </Text>
            </ScrollView>
          )}
        </View>

        <View style={styles.footer}>
          <Text style={styles.footerText}>
            {updatedAt ? `Last checked ${updatedAt.toLocaleTimeString()}` : "Connecting..."}
          </Text>
          <Text style={styles.footerText}>Controls, approvals, stops, and dispatches stay off-phone.</Text>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: { flex: 1, backgroundColor: "#07110f" },
  page: { flexGrow: 1, paddingHorizontal: 18, paddingBottom: 34, paddingTop: 18 },
  header: { alignItems: "center", flexDirection: "row", justifyContent: "space-between" },
  eyebrow: { color: "#66e3c4", fontSize: 12, fontWeight: "800" },
  title: { color: "#f2fff9", fontSize: 30, fontWeight: "700" },
  badge: {
    backgroundColor: "#17342c",
    borderColor: "#2d6a59",
    borderRadius: 8,
    borderWidth: 1,
    paddingHorizontal: 10,
    paddingVertical: 7,
  },
  badgeText: { color: "#b7ffe9", fontSize: 10, fontWeight: "800" },
  subtitle: { color: "#b8c9c3", fontSize: 15, marginTop: 16 },
  endpoint: { color: "#7f918c", fontFamily: "monospace", fontSize: 11, marginTop: 8 },
  grid: { flexDirection: "row", flexWrap: "wrap", gap: 8, paddingVertical: 20 },
  tile: {
    backgroundColor: "#0d1c18",
    borderColor: "#19332b",
    borderRadius: 8,
    borderWidth: 1,
    minHeight: 82,
    padding: 12,
    width: "48.5%",
  },
  activeTile: { backgroundColor: "#17342c", borderColor: "#3a826d" },
  dot: { borderRadius: 4, height: 8, marginBottom: 10, width: 8 },
  okDot: { backgroundColor: "#66e3c4" },
  errorDot: { backgroundColor: "#ff9a7d" },
  tileLabel: { color: "#e9fff7", fontSize: 14, fontWeight: "700" },
  activeTileLabel: { color: "#ffffff" },
  tileValue: { color: "#8ea69d", fontSize: 12, marginTop: 4 },
  panel: {
    backgroundColor: "#0b1815",
    borderColor: "#1d392f",
    borderRadius: 8,
    borderWidth: 1,
    minHeight: 360,
    padding: 16,
  },
  panelHeader: { alignItems: "center", flexDirection: "row", justifyContent: "space-between", marginBottom: 16 },
  panelTitle: { color: "#f2fff9", fontSize: 22, fontWeight: "700" },
  path: { color: "#7f918c", fontFamily: "monospace", fontSize: 11, marginTop: 4 },
  payloadScroller: { flexGrow: 0 },
  payload: { color: "#d2dfdb", fontFamily: "monospace", fontSize: 12, lineHeight: 19 },
  errorPanel: { backgroundColor: "#281713", borderColor: "#63352b", borderRadius: 8, borderWidth: 1, padding: 14 },
  errorTitle: { color: "#ffb6a5", fontSize: 16, fontWeight: "700" },
  errorText: { color: "#ffd2c8", fontFamily: "monospace", fontSize: 12, marginTop: 7 },
  errorHint: { color: "#c99e93", fontSize: 13, lineHeight: 19, marginTop: 14 },
  footer: { gap: 6, marginTop: 16 },
  footerText: { color: "#7f918c", fontSize: 12, lineHeight: 17 },
});

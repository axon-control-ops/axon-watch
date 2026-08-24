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
  TextInput,
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
  { key: "workspaces", label: "Workspaces", path: "/api/workspaces?scope=operator" },
  { key: "agents", label: "Fleet", path: "/api/agents?scope=operator" },
] as const;

type SurfaceKey = (typeof SURFACES)[number]["key"];
type Snapshot = Partial<Record<SurfaceKey, unknown>>;
type Failures = Partial<Record<SurfaceKey, string>>;
type SummaryTone = "ok" | "warn" | "error" | "neutral";
type RunAction = "approve" | "reject" | "resume" | "stop";

type SummaryStat = {
  label: string;
  value: string;
  tone?: SummaryTone;
};

type FocusCard = {
  title: string;
  detail: string;
  tone: SummaryTone;
};

type ActionState = {
  kind: "idle" | "working" | "success" | "error";
  message: string;
};

function compactJson(value: unknown): string {
  if (value === undefined) return "No data returned.";
  return JSON.stringify(value, null, 2);
}

function asRecord(value: unknown): Record<string, unknown> | null {
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : null;
}

function asArray(value: unknown): unknown[] {
  return Array.isArray(value) ? value : [];
}

function readCount(value: unknown, keys: string[]): number | null {
  const record = asRecord(value);
  if (!record) return null;
  for (const key of keys) {
    const next = record[key];
    if (typeof next === "number" && Number.isFinite(next)) return next;
    if (Array.isArray(next)) return next.length;
    const nested = asRecord(next);
    if (nested) {
      const nestedCount = readCount(nested, ["count", "total", "items", "runs", "pending"]);
      if (nestedCount !== null) return nestedCount;
    }
  }
  return null;
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

function statusTone(input: boolean | null): SummaryTone {
  if (input === true) return "ok";
  if (input === false) return "error";
  return "neutral";
}

function formatClock(value: Date | null): string {
  return value ? value.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : "Waiting";
}

function recordId(record: Record<string, unknown>): string {
  if (typeof record.run_id === "string") return record.run_id;
  if (typeof record.workspace_id === "string") return record.workspace_id;
  if (typeof record.id === "string") return record.id;
  return "item";
}

function collectWorkspaceItems(snapshot: Snapshot): Record<string, unknown>[] {
  const workspaces = asRecord(snapshot.workspaces);
  return workspaces ? asArray(workspaces.items) as Record<string, unknown>[] : [];
}

function collectRunItems(snapshot: Snapshot, workspaceId: string | null): Record<string, unknown>[] {
  const runs = asRecord(snapshot.runs);
  const items = runs ? (asArray(runs.items ?? runs.runs) as Record<string, unknown>[]) : [];
  if (!workspaceId) return items;
  const filtered = items.filter((item) => item.workspace_id === workspaceId);
  return filtered.length > 0 ? filtered : items;
}

function buildTopStats(snapshot: Snapshot, failures: Failures, workspaceId: string | null): SummaryStat[] {
  const health = asRecord(snapshot.health);
  const runtime = asRecord(snapshot.runtime);
  const runs = collectRunItems(snapshot, workspaceId);
  const inbox = asRecord(snapshot.inbox);
  const workspaces = collectWorkspaceItems(snapshot);
  const agents = asRecord(snapshot.agents);
  const healthOk = health?.status === "ok";
  const runtimeReady =
    typeof runtime?.ready === "boolean"
      ? runtime.ready
      : typeof asRecord(runtime?.control_plane)?.ready === "boolean"
        ? (asRecord(runtime?.control_plane)?.ready as boolean)
        : null;
  const inboxCount = readCount(inbox, ["items", "signals", "count", "total", "pending"]);
  const fleetCount = readCount(agents, ["items", "agents", "count", "total"]);

  return [
    {
      label: "Health",
      value: failures.health ? "Offline" : healthOk ? "Healthy" : summarizeSurface(snapshot.health),
      tone: failures.health ? "error" : healthOk ? "ok" : "warn",
    },
    {
      label: "Runtime",
      value: failures.runtime ? "Blocked" : runtimeReady === true ? "Ready" : runtimeReady === false ? "Not ready" : summarizeSurface(snapshot.runtime),
      tone: failures.runtime ? "error" : statusTone(runtimeReady),
    },
    {
      label: "Runs",
      value: failures.runs ? "Unavailable" : `${runs.length}`,
      tone: failures.runs ? "error" : runs.some((run) => run.phase === "awaiting_approval") ? "warn" : "neutral",
    },
    {
      label: "Workspaces",
      value: failures.workspaces ? "Unavailable" : `${workspaces.length}`,
      tone: failures.workspaces ? "error" : workspaces.length > 0 ? "ok" : "neutral",
    },
    {
      label: "Fleet",
      value: failures.agents ? "Unavailable" : fleetCount === null ? summarizeSurface(snapshot.agents) : `${fleetCount}`,
      tone: failures.agents ? "error" : "neutral",
    },
    {
      label: "Inbox",
      value: failures.inbox ? "Unavailable" : inboxCount === null ? summarizeSurface(snapshot.inbox) : `${inboxCount}`,
      tone: failures.inbox ? "error" : inboxCount && inboxCount > 0 ? "warn" : "ok",
    },
  ];
}

function buildFocusCard(snapshot: Snapshot, failures: Failures, workspaceId: string | null): FocusCard {
  if (failures.briefing) {
    return {
      title: "Briefing unavailable",
      detail: failures.briefing,
      tone: "error",
    };
  }

  const briefing = asRecord(snapshot.briefing);
  if (!briefing) {
    return {
      title: "Waiting for briefing",
      detail: "Pull to refresh once the control plane is reachable.",
      tone: "neutral",
    };
  }

  const approvals = readCount(briefing, ["pending_approvals", "approvals", "pending"]);
  const signals = readCount(briefing, ["signals", "inbox", "open_signals", "attention"]);
  const presence = asRecord(briefing.operator_presence);
  const spoken = asRecord(presence?.spoken_alert);
  const message =
    typeof spoken?.message === "string" && spoken.message.trim().length > 0
      ? spoken.message.trim()
      : typeof presence?.persona_voice_line === "string" && presence.persona_voice_line.trim().length > 0
        ? presence.persona_voice_line.trim()
        : null;

  if ((approvals ?? 0) > 0) {
    return {
      title: `${approvals} approval${approvals === 1 ? "" : "s"} need review`,
      detail:
        message ??
        (workspaceId
          ? `The control plane is waiting on a decision in ${workspaceId}.`
          : "The control plane is waiting on a bounded decision."),
      tone: "warn",
    };
  }

  if ((signals ?? 0) > 0) {
    return {
      title: `${signals} attention item${signals === 1 ? "" : "s"} open`,
      detail: message ?? "Open signals are present in the briefing feed.",
      tone: "warn",
    };
  }

  return {
    title: "Companion is watching",
    detail: message ?? "No urgent approvals or attention items are surfaced right now.",
    tone: "ok",
  };
}

function buildRunCard(snapshot: Snapshot, failures: Failures, workspaceId: string | null): FocusCard {
  if (failures.runs) {
    return {
      title: "Runs unavailable",
      detail: failures.runs,
      tone: "error",
    };
  }

  const firstRun = collectRunItems(snapshot, workspaceId)[0];
  if (!firstRun) {
    return {
      title: "No active run surfaced",
      detail: "The run feed is reachable but does not show a current item yet.",
      tone: "neutral",
    };
  }

  const id = typeof firstRun.run_id === "string" ? firstRun.run_id : typeof firstRun.id === "string" ? firstRun.id : "run";
  const phase = typeof firstRun.phase === "string" ? firstRun.phase : "active";
  const summary =
    typeof firstRun.summary === "string"
      ? firstRun.summary
      : typeof firstRun.title === "string"
        ? firstRun.title
        : `Top run is ${phase}.`;

  return {
    title: `${id} · ${phase}`,
    detail: summary,
    tone: phase === "failed" ? "error" : phase === "awaiting_approval" ? "warn" : "ok",
  };
}

function toneStyle(tone: SummaryTone) {
  switch (tone) {
    case "ok":
      return styles.toneOk;
    case "warn":
      return styles.toneWarn;
    case "error":
      return styles.toneError;
    default:
      return styles.toneNeutral;
  }
}

function surfacePath(
  surface: { key: SurfaceKey; path: string },
  workspaceId: string | null,
): string {
  if (!workspaceId) return surface.path;
  if (surface.key === "briefing") return `/api/briefing?workspace_id=${encodeURIComponent(workspaceId)}`;
  return surface.path;
}

async function fetchJson(path: string, init?: RequestInit): Promise<unknown> {
  const response = await fetch(`${CONTROL_PLANE_URL}${path}`, {
    headers: {
      Accept: "application/json",
      ...(init?.body ? { "Content-Type": "application/json" } : {}),
      ...(init?.headers ?? {}),
    },
    ...init,
  });

  if (!response.ok) {
    const message = await response.text();
    throw new Error(message.trim() || `HTTP ${response.status}`);
  }
  return response.json();
}

function workspaceLabel(record: Record<string, unknown>): string {
  if (typeof record.display_name === "string" && record.display_name.trim()) return record.display_name;
  if (typeof record.workspace_id === "string") return record.workspace_id;
  return "workspace";
}

function employeeSummary(employee: Record<string, unknown>): string {
  const role = typeof employee.role_label === "string" ? employee.role_label : typeof employee.role === "string" ? employee.role : "Employee";
  const status = typeof employee.status === "string" ? employee.status.replace(/_/g, " ") : "idle";
  const owns = typeof employee.owns === "string" ? employee.owns : "";
  return owns ? `${role} · ${status} · ${owns}` : `${role} · ${status}`;
}

export default function App() {
  const [active, setActive] = useState<SurfaceKey>("health");
  const [snapshot, setSnapshot] = useState<Snapshot>({});
  const [failures, setFailures] = useState<Failures>({});
  const [refreshing, setRefreshing] = useState(false);
  const [updatedAt, setUpdatedAt] = useState<Date | null>(null);
  const [selectedWorkspaceId, setSelectedWorkspaceId] = useState<string | null>(null);
  const [workspaceCompany, setWorkspaceCompany] = useState<unknown>(null);
  const [workspaceCompanyError, setWorkspaceCompanyError] = useState<string | null>(null);
  const [actionState, setActionState] = useState<ActionState>({ kind: "idle", message: "" });
  const [draftSummary, setDraftSummary] = useState("Mobile operator run");
  const [draftDetail, setDraftDetail] = useState("Created from the phone for quick control-plane work.");

  const refresh = useCallback(async () => {
    setRefreshing(true);
    try {
      const results = await Promise.all(
        SURFACES.map(async (surface) => {
          try {
            return {
              key: surface.key,
              data: await fetchJson(surfacePath(surface, selectedWorkspaceId)),
            } as const;
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

      const workspaces = asRecord(nextSnapshot.workspaces);
      const workspaceItems = workspaces ? (asArray(workspaces.items) as Record<string, unknown>[]) : [];
      if (!selectedWorkspaceId || !workspaceItems.some((item) => item.workspace_id === selectedWorkspaceId)) {
        const firstWorkspaceId =
          typeof workspaceItems[0]?.workspace_id === "string" ? (workspaceItems[0].workspace_id as string) : null;
        setSelectedWorkspaceId(firstWorkspaceId);
      }
    } finally {
      setRefreshing(false);
    }
  }, [selectedWorkspaceId]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  useEffect(() => {
    if (!selectedWorkspaceId) {
      setWorkspaceCompany(null);
      setWorkspaceCompanyError(null);
      return;
    }

    let cancelled = false;
    void (async () => {
      try {
        const data = await fetchJson(`/api/workspaces/${encodeURIComponent(selectedWorkspaceId)}/company`);
        if (!cancelled) {
          setWorkspaceCompany(data);
          setWorkspaceCompanyError(null);
        }
      } catch (error) {
        if (!cancelled) {
          const message = error instanceof Error ? error.message : "Request failed";
          setWorkspaceCompany(null);
          setWorkspaceCompanyError(explainFetchFailure(message, CONTROL_PLANE_URL));
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [selectedWorkspaceId, updatedAt]);

  const selected = useMemo(
    () => SURFACES.find((surface) => surface.key === active) ?? SURFACES[0],
    [active],
  );
  const selectedError = failures[active];
  const topStats = useMemo(
    () => buildTopStats(snapshot, failures, selectedWorkspaceId),
    [snapshot, failures, selectedWorkspaceId],
  );
  const focusCard = useMemo(
    () => buildFocusCard(snapshot, failures, selectedWorkspaceId),
    [snapshot, failures, selectedWorkspaceId],
  );
  const runCard = useMemo(
    () => buildRunCard(snapshot, failures, selectedWorkspaceId),
    [snapshot, failures, selectedWorkspaceId],
  );
  const workspaces = useMemo(() => collectWorkspaceItems(snapshot), [snapshot]);
  const runs = useMemo(() => collectRunItems(snapshot, selectedWorkspaceId), [snapshot, selectedWorkspaceId]);
  const topRun = runs[0] ?? null;
  const companyRecord = asRecord(workspaceCompany);
  const company = asRecord(companyRecord?.company);
  const employees = company ? (asArray(company.employees) as Record<string, unknown>[]) : [];

  const runAction = useCallback(
    async (action: RunAction) => {
      if (!topRun || typeof topRun.run_id !== "string") return;
      setActionState({ kind: "working", message: `${action}ing ${topRun.run_id}...` });
      try {
        await fetchJson(`/api/runs/${encodeURIComponent(topRun.run_id)}/${action}`, { method: "POST" });
        setActionState({ kind: "success", message: `${action}ed ${topRun.run_id}.` });
        await refresh();
      } catch (error) {
        const message = error instanceof Error ? error.message : "Request failed";
        setActionState({ kind: "error", message: explainFetchFailure(message, CONTROL_PLANE_URL) });
      }
    },
    [refresh, topRun],
  );

  const startRun = useCallback(async () => {
    if (!selectedWorkspaceId) return;
    const summary = draftSummary.trim();
    if (!summary) {
      setActionState({ kind: "error", message: "A run summary is required." });
      return;
    }

    setActionState({ kind: "working", message: `Starting a run in ${selectedWorkspaceId}...` });
    try {
      await fetchJson("/api/runs", {
        method: "POST",
        body: JSON.stringify({
          workspace_id: selectedWorkspaceId,
          summary,
          detail: draftDetail.trim() || undefined,
          mode: "agent",
        }),
      });
      setActionState({ kind: "success", message: `Started a run in ${selectedWorkspaceId}.` });
      await refresh();
    } catch (error) {
      const message = error instanceof Error ? error.message : "Request failed";
      setActionState({ kind: "error", message: explainFetchFailure(message, CONTROL_PLANE_URL) });
    }
  }, [draftDetail, draftSummary, refresh, selectedWorkspaceId]);

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
            <Text style={styles.title}>Mobile Cockpit</Text>
          </View>
          <View style={styles.badge}>
            <Text style={styles.badgeText}>BASIC CONTROL</Text>
          </View>
        </View>

        <Text style={styles.subtitle}>Start runs, handle approvals, and check the selected workspace fleet from the phone.</Text>
        <Text numberOfLines={1} style={styles.endpoint}>
          {CONTROL_PLANE_URL}
        </Text>

        <View style={styles.heroCard}>
          <View style={styles.heroHeader}>
            <Text style={styles.heroEyebrow}>Now</Text>
            <Text style={styles.heroTime}>{formatClock(updatedAt)}</Text>
          </View>
          <Text style={styles.heroTitle}>{focusCard.title}</Text>
          <Text style={styles.heroBody}>{focusCard.detail}</Text>
          <View style={styles.heroRule} />
          <Text style={styles.heroFoot}>
            Phone-side controls are limited to basic run lifecycle actions and workspace checks.
          </Text>
        </View>

        <View style={styles.statsRow}>
          {topStats.map((stat) => (
            <View key={stat.label} style={styles.statCard}>
              <View style={[styles.statDot, toneStyle(stat.tone ?? "neutral")]} />
              <Text style={styles.statLabel}>{stat.label}</Text>
              <Text style={styles.statValue}>{stat.value}</Text>
            </View>
          ))}
        </View>

        <View style={styles.panel}>
          <Text style={styles.panelTitle}>Workspace</Text>
          <Text style={styles.panelCopy}>Choose the workspace you want the phone controls to target.</Text>
          <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.chipRow}>
            {workspaces.map((workspace) => {
              const workspaceId =
                typeof workspace.workspace_id === "string" ? workspace.workspace_id : recordId(workspace);
              const selectedWorkspace = workspaceId === selectedWorkspaceId;
              return (
                <Pressable
                  key={workspaceId}
                  accessibilityRole="button"
                  accessibilityState={{ selected: selectedWorkspace }}
                  onPress={() => setSelectedWorkspaceId(workspaceId)}
                  style={[styles.chip, selectedWorkspace && styles.chipActive]}
                >
                  <Text style={[styles.chipText, selectedWorkspace && styles.chipTextActive]}>
                    {workspaceLabel(workspace)}
                  </Text>
                </Pressable>
              );
            })}
          </ScrollView>
          {selectedWorkspaceId ? (
            <Text style={styles.panelMeta}>Targeting {selectedWorkspaceId}</Text>
          ) : (
            <Text style={styles.panelMeta}>No workspace surfaced yet.</Text>
          )}
        </View>

        <View style={styles.focusRow}>
          <View style={styles.focusPanel}>
            <Text style={styles.focusLabel}>Top run</Text>
            <Text style={styles.focusTitle}>{runCard.title}</Text>
            <Text style={styles.focusBody}>{runCard.detail}</Text>
          </View>
          <View style={styles.focusPanel}>
            <Text style={styles.focusLabel}>Briefing</Text>
            <Text style={styles.focusTitle}>{focusCard.title}</Text>
            <Text style={styles.focusBody}>{focusCard.detail}</Text>
          </View>
        </View>

        <View style={styles.panel}>
          <Text style={styles.panelTitle}>Run controls</Text>
          <Text style={styles.panelCopy}>Start a basic run, then approve, reject, resume, or stop the top run for the selected workspace.</Text>
          <TextInput
            style={styles.input}
            value={draftSummary}
            onChangeText={setDraftSummary}
            placeholder="Run summary"
            placeholderTextColor="#6d857d"
          />
          <TextInput
            style={[styles.input, styles.inputMultiline]}
            value={draftDetail}
            onChangeText={setDraftDetail}
            placeholder="Run detail"
            placeholderTextColor="#6d857d"
            multiline
          />
          <Pressable
            accessibilityRole="button"
            onPress={() => void startRun()}
            style={[styles.actionButton, !selectedWorkspaceId && styles.actionButtonDisabled]}
            disabled={!selectedWorkspaceId || actionState.kind === "working"}
          >
            <Text style={styles.actionButtonText}>Start run</Text>
          </Pressable>
          <View style={styles.actionRow}>
            <Pressable
              accessibilityRole="button"
              onPress={() => void runAction("approve")}
              style={[styles.actionButtonSecondary, !topRun && styles.actionButtonDisabled]}
              disabled={!topRun || actionState.kind === "working"}
            >
              <Text style={styles.actionButtonText}>Approve</Text>
            </Pressable>
            <Pressable
              accessibilityRole="button"
              onPress={() => void runAction("reject")}
              style={[styles.actionButtonSecondary, !topRun && styles.actionButtonDisabled]}
              disabled={!topRun || actionState.kind === "working"}
            >
              <Text style={styles.actionButtonText}>Reject</Text>
            </Pressable>
            <Pressable
              accessibilityRole="button"
              onPress={() => void runAction("resume")}
              style={[styles.actionButtonSecondary, !topRun && styles.actionButtonDisabled]}
              disabled={!topRun || actionState.kind === "working"}
            >
              <Text style={styles.actionButtonText}>Resume</Text>
            </Pressable>
            <Pressable
              accessibilityRole="button"
              onPress={() => void runAction("stop")}
              style={[styles.actionButtonSecondary, !topRun && styles.actionButtonDisabled]}
              disabled={!topRun || actionState.kind === "working"}
            >
              <Text style={styles.actionButtonText}>Stop</Text>
            </Pressable>
          </View>
          {actionState.kind !== "idle" ? (
            <Text
              style={[
                styles.statusMessage,
                actionState.kind === "error"
                  ? styles.statusError
                  : actionState.kind === "success"
                    ? styles.statusSuccess
                    : styles.statusWorking,
              ]}
            >
              {actionState.message}
            </Text>
          ) : null}
        </View>

        <View style={styles.panel}>
          <Text style={styles.panelTitle}>Workspace fleet</Text>
          <Text style={styles.panelCopy}>This is the company roster for the selected workspace.</Text>
          {workspaceCompanyError ? (
            <View style={styles.errorPanel}>
              <Text style={styles.errorTitle}>Unavailable</Text>
              <Text style={styles.errorText}>{workspaceCompanyError}</Text>
            </View>
          ) : employees.length > 0 ? (
            <View style={styles.list}>
              {employees.map((employee) => {
                const employeeId =
                  typeof employee.employee_id === "string" ? employee.employee_id : recordId(employee);
                return (
                  <View key={employeeId} style={styles.listItem}>
                    <Text style={styles.listTitle}>
                      {typeof employee.name === "string" ? employee.name : employeeId}
                    </Text>
                    <Text style={styles.listDetail}>{employeeSummary(employee)}</Text>
                  </View>
                );
              })}
            </View>
          ) : (
            <Text style={styles.panelMeta}>No roster is available for this workspace yet.</Text>
          )}
        </View>

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
              <Text style={styles.path}>{surfacePath(selected, selectedWorkspaceId)}</Text>
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
          <Text style={styles.footerText}>Pull to refresh after network, tunnel, or local control-plane changes.</Text>
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
  heroCard: {
    backgroundColor: "#10211d",
    borderColor: "#24443a",
    borderRadius: 18,
    borderWidth: 1,
    marginTop: 18,
    overflow: "hidden",
    padding: 18,
  },
  heroHeader: { alignItems: "center", flexDirection: "row", justifyContent: "space-between" },
  heroEyebrow: { color: "#8ab9aa", fontSize: 12, fontWeight: "700", letterSpacing: 0.8, textTransform: "uppercase" },
  heroTime: { color: "#d6fff1", fontSize: 13, fontWeight: "600" },
  heroTitle: { color: "#f3fff9", fontSize: 24, fontWeight: "700", marginTop: 14 },
  heroBody: { color: "#c6d8d1", fontSize: 14, lineHeight: 21, marginTop: 10 },
  heroRule: { backgroundColor: "#214138", height: 1, marginTop: 16, width: "100%" },
  heroFoot: { color: "#8aa198", fontSize: 12, lineHeight: 18, marginTop: 12 },
  statsRow: { flexDirection: "row", flexWrap: "wrap", gap: 10, marginTop: 16 },
  statCard: {
    backgroundColor: "#0d1c18",
    borderColor: "#19332b",
    borderRadius: 14,
    borderWidth: 1,
    minHeight: 88,
    padding: 12,
    width: "47%",
  },
  statDot: { borderRadius: 4, height: 8, marginBottom: 10, width: 8 },
  statLabel: { color: "#9ab4aa", fontSize: 12, fontWeight: "700", textTransform: "uppercase" },
  statValue: { color: "#effff8", fontSize: 20, fontWeight: "700", marginTop: 8 },
  toneOk: { backgroundColor: "#66e3c4" },
  toneWarn: { backgroundColor: "#ffd166" },
  toneError: { backgroundColor: "#ff9a7d" },
  toneNeutral: { backgroundColor: "#5f756d" },
  panel: {
    backgroundColor: "#0b1815",
    borderColor: "#1d392f",
    borderRadius: 14,
    borderWidth: 1,
    marginTop: 16,
    minHeight: 120,
    padding: 16,
  },
  panelHeader: { alignItems: "center", flexDirection: "row", justifyContent: "space-between", marginBottom: 16 },
  panelTitle: { color: "#f2fff9", fontSize: 22, fontWeight: "700" },
  panelCopy: { color: "#a6beb6", fontSize: 13, lineHeight: 19, marginTop: 8 },
  panelMeta: { color: "#7f918c", fontSize: 12, marginTop: 12 },
  chipRow: { gap: 10, paddingTop: 14, paddingBottom: 4 },
  chip: {
    backgroundColor: "#0d1c18",
    borderColor: "#224036",
    borderRadius: 999,
    borderWidth: 1,
    paddingHorizontal: 14,
    paddingVertical: 10,
  },
  chipActive: { backgroundColor: "#17342c", borderColor: "#3a826d" },
  chipText: { color: "#d6fff1", fontSize: 13, fontWeight: "700" },
  chipTextActive: { color: "#ffffff" },
  focusRow: { gap: 10, marginTop: 16 },
  focusPanel: {
    backgroundColor: "#0b1815",
    borderColor: "#1d392f",
    borderRadius: 14,
    borderWidth: 1,
    padding: 14,
  },
  focusLabel: { color: "#86a59a", fontSize: 11, fontWeight: "700", textTransform: "uppercase" },
  focusTitle: { color: "#f2fff9", fontSize: 18, fontWeight: "700", marginTop: 8 },
  focusBody: { color: "#b8c9c3", fontSize: 13, lineHeight: 19, marginTop: 8 },
  input: {
    backgroundColor: "#10211d",
    borderColor: "#224036",
    borderRadius: 12,
    borderWidth: 1,
    color: "#f2fff9",
    fontSize: 14,
    marginTop: 14,
    paddingHorizontal: 12,
    paddingVertical: 12,
  },
  inputMultiline: { minHeight: 92, textAlignVertical: "top" },
  actionButton: {
    alignItems: "center",
    backgroundColor: "#2f9f80",
    borderRadius: 12,
    marginTop: 14,
    paddingHorizontal: 14,
    paddingVertical: 12,
  },
  actionButtonSecondary: {
    alignItems: "center",
    backgroundColor: "#17342c",
    borderColor: "#2d6a59",
    borderRadius: 12,
    borderWidth: 1,
    flexGrow: 1,
    minWidth: "47%",
    paddingHorizontal: 14,
    paddingVertical: 12,
  },
  actionButtonDisabled: { opacity: 0.45 },
  actionButtonText: { color: "#f4fff9", fontSize: 14, fontWeight: "800" },
  actionRow: { flexDirection: "row", flexWrap: "wrap", gap: 10, marginTop: 10 },
  statusMessage: { fontSize: 13, lineHeight: 19, marginTop: 12 },
  statusSuccess: { color: "#87f2c7" },
  statusError: { color: "#ffb6a5" },
  statusWorking: { color: "#d9f7ee" },
  list: { gap: 10, marginTop: 14 },
  listItem: {
    backgroundColor: "#0d1c18",
    borderColor: "#19332b",
    borderRadius: 12,
    borderWidth: 1,
    padding: 12,
  },
  listTitle: { color: "#f2fff9", fontSize: 15, fontWeight: "700" },
  listDetail: { color: "#9eb6ae", fontSize: 12, lineHeight: 18, marginTop: 6 },
  grid: { flexDirection: "row", flexWrap: "wrap", gap: 8, paddingTop: 20 },
  tile: {
    backgroundColor: "#0d1c18",
    borderColor: "#19332b",
    borderRadius: 12,
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

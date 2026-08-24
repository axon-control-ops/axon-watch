import { StatusBar } from "expo-status-bar";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  ActivityIndicator,
  FlatList,
  Image,
  Modal,
  Platform,
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
import vaxonOrbCinematic from "./vaxon-orb-cinematic.png";

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

// What tapping each Overview stat tile does. Keyed by the tile's own label
// (buildTopStats), not by SURFACES.key/label -- SURFACES.label ("Fleet") is
// the raw-endpoint name shown in the Data tab; this is the human tile label
// shown on Overview, which was deliberately reworded to "Leads" there since
// /api/agents?scope=operator returns one lead per workspace, not a headcount.
const STAT_TILE_ACTIONS: Record<string, "data" | "runs" | "workspaces" | "fleet" | "inbox"> = {
  Health: "data",
  Runtime: "data",
  Runs: "runs",
  Workspaces: "workspaces",
  Leads: "fleet",
  Inbox: "inbox",
};

type SurfaceKey = (typeof SURFACES)[number]["key"];
type Snapshot = Partial<Record<SurfaceKey, unknown>>;
type Failures = Partial<Record<SurfaceKey, string>>;
type SummaryTone = "ok" | "warn" | "error" | "neutral";
type RunAction = "approve" | "reject" | "resume" | "stop";
type CockpitMode = "overview" | "command" | "fleet" | "data";
type CommandSource = "typed" | "voice" | "quick";
type CommandStatus = "queued" | "sent" | "failed";
type VoiceState =
  | "idle"
  | "listening"
  | "processing"
  | "success"
  | "permission_denied"
  | "unavailable"
  | "failure";
type OperatorSessionIdentity = "local" | "loopback" | "operator" | "session" | null;

type OperatorSessionStatus = {
  authenticated: boolean;
  auth_required: boolean;
  identity: OperatorSessionIdentity;
  auth_mode?: string;
  loopback_bypass?: boolean;
  cookie_max_age_seconds?: number;
  password_enabled?: boolean;
  token_enabled?: boolean;
  session_token?: string;
};

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

type CommandEntry = {
  id: string;
  source: CommandSource;
  status: CommandStatus;
  text: string;
  time: Date;
  response: string;
};

type VaxonAdvisory = {
  title: string;
  detail: string;
  tone: SummaryTone;
  intent: string;
};

type SpeechRecognitionEventLike = {
  results?: ArrayLike<ArrayLike<{ transcript?: string }>>;
};

type SpeechRecognitionErrorLike = {
  error?: string;
  message?: string;
};

type SpeechRecognitionLike = {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  maxAlternatives: number;
  onresult: ((event: SpeechRecognitionEventLike) => void) | null;
  onerror: ((event: SpeechRecognitionErrorLike) => void) | null;
  onend: (() => void) | null;
  start: () => void;
  stop: () => void;
  abort?: () => void;
};

type SpeechRecognitionConstructor = new () => SpeechRecognitionLike;

const COCKPIT_MODES: { key: CockpitMode; label: string; eyebrow: string }[] = [
  { key: "overview", label: "Overview", eyebrow: "Observe" },
  { key: "command", label: "Command", eyebrow: "Act" },
  { key: "fleet", label: "Fleet", eyebrow: "Team" },
  { key: "data", label: "Data", eyebrow: "Verify" },
];

const QUICK_COMMANDS = [
  "REPORT: brief me on attention, active runs, and next move.",
  "Inspect the selected workspace and identify the highest-risk blocker.",
  "Prepare a narrow recovery plan for the top failed run.",
] as const;

type RunActionAvailability = Record<RunAction, boolean>;

function speechRecognitionConstructor(): SpeechRecognitionConstructor | null {
  if (Platform.OS !== "web") return null;
  const host = globalThis as typeof globalThis & {
    SpeechRecognition?: SpeechRecognitionConstructor;
    webkitSpeechRecognition?: SpeechRecognitionConstructor;
  };
  return host.SpeechRecognition ?? host.webkitSpeechRecognition ?? null;
}

function commandEntryId(): string {
  return `cmd-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

function commandTitle(source: CommandSource): string {
  if (source === "voice") return "Voice command";
  if (source === "quick") return "Quick command";
  return "Typed command";
}

function voiceStateLabel(state: VoiceState): string {
  switch (state) {
    case "listening":
      return "Listening";
    case "processing":
      return "Processing";
    case "success":
      return "Command captured";
    case "permission_denied":
      return "Mic denied";
    case "unavailable":
      return "Voice unavailable";
    case "failure":
      return "Voice failed";
    default:
      return "Voice standby";
  }
}

function voiceStateCopy(state: VoiceState, message: string): string {
  if (message.trim()) return message.trim();
  switch (state) {
    case "listening":
      return "Speak a short command. VAXON will convert it into a scoped mobile run.";
    case "processing":
      return "Parsing the captured instruction and preparing command context.";
    case "success":
      return "Voice instruction was added to the command stream.";
    case "permission_denied":
      return "Microphone permission was denied. Enable mic access for this app and try again.";
    case "unavailable":
      return "This runtime does not expose speech recognition. Use the composer or run Expo web in a browser with speech support.";
    case "failure":
      return "No usable command was captured. Try a shorter instruction.";
    default:
      return "Tap mic to speak, or type the instruction below.";
  }
}

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

function collectInboxItems(snapshot: Snapshot): Record<string, unknown>[] {
  const inbox = asRecord(snapshot.inbox);
  return inbox ? (asArray(inbox.items) as Record<string, unknown>[]) : [];
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
  // /api/agents?scope=operator returns one representative (primary/lead)
  // agent per workspace, not a headcount -- verified live: 18 items, one per
  // workspace_id. A bare "Fleet: 18" reads as a total employee count and
  // isn't one, so it needs the phrase, not just the label, to be honest.
  const fleetCount = readCount(agents, ["items", "agents", "count", "total"]);
  const awaitingApproval = runs.filter((run) => run.phase === "awaiting_approval").length;
  const runningNow = runs.filter((run) => run.phase === "executing" || run.phase === "running").length;

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
      value: failures.runs
        ? "Unavailable"
        : runs.length === 0
          ? "None active"
          : awaitingApproval > 0
            ? `${awaitingApproval} need approval`
            : `${runningNow} running`,
      tone: failures.runs ? "error" : awaitingApproval > 0 ? "warn" : "neutral",
    },
    {
      label: "Workspaces",
      value: failures.workspaces ? "Unavailable" : `${workspaces.length} online`,
      tone: failures.workspaces ? "error" : workspaces.length > 0 ? "ok" : "neutral",
    },
    {
      label: "Leads",
      value: failures.agents ? "Unavailable" : fleetCount === null ? summarizeSurface(snapshot.agents) : `${fleetCount} assigned`,
      tone: failures.agents ? "error" : "neutral",
    },
    {
      label: "Inbox",
      value: failures.inbox ? "Unavailable" : inboxCount === null ? summarizeSurface(snapshot.inbox) : inboxCount === 0 ? "All clear" : `${inboxCount} need review`,
      tone: failures.inbox ? "error" : inboxCount && inboxCount > 0 ? "warn" : "ok",
    },
  ];
}

/**
 * One plain-English sentence synthesizing the same six numbers the stat
 * tiles show, in the same voice as the VAXON Advisory card above it -- the
 * tile grid on its own was a wall of bare counts with no read on what they
 * meant together or what to do about it.
 */
function buildSituationSummary(snapshot: Snapshot, failures: Failures, workspaceId: string | null): string {
  const health = asRecord(snapshot.health);
  const runtime = asRecord(snapshot.runtime);
  const runs = collectRunItems(snapshot, workspaceId);
  const inbox = asRecord(snapshot.inbox);
  const workspaces = collectWorkspaceItems(snapshot);
  const healthOk = health?.status === "ok";
  const runtimeReady =
    typeof runtime?.ready === "boolean"
      ? runtime.ready
      : typeof asRecord(runtime?.control_plane)?.ready === "boolean"
        ? (asRecord(runtime?.control_plane)?.ready as boolean)
        : null;
  const inboxCount = readCount(inbox, ["items", "signals", "count", "total", "pending"]) ?? 0;
  const awaitingApproval = runs.filter((run) => run.phase === "awaiting_approval").length;
  const failedRuns = runs.filter((run) => run.phase === "failed").length;
  const runningNow = runs.filter((run) => run.phase === "executing" || run.phase === "running").length;

  if (failures.health || failures.runtime) {
    return "Can't reach the control plane right now — pull to refresh once it's back.";
  }

  const openIssues: string[] = [];
  if (!healthOk) openIssues.push("control plane is reporting unhealthy");
  if (runtimeReady === false) openIssues.push("runtime isn't ready to dispatch");
  if (failedRuns > 0) openIssues.push(`${failedRuns} run${failedRuns === 1 ? "" : "s"} failed and need${failedRuns === 1 ? "s" : ""} triage`);
  if (awaitingApproval > 0) openIssues.push(`${awaitingApproval} waiting on your approval`);

  if (openIssues.length > 0) {
    return `${openIssues[0].charAt(0).toUpperCase()}${openIssues[0].slice(1)}${openIssues.length > 1 ? `, and ${openIssues.length - 1} other thing${openIssues.length > 2 ? "s" : ""} need${openIssues.length === 2 ? "s" : ""} attention` : ""}. ${inboxCount > 0 ? `${inboxCount} inbox item${inboxCount === 1 ? "" : "s"} also waiting.` : ""}`.trim();
  }

  const runsPhrase = runningNow > 0 ? `${runningNow} run${runningNow === 1 ? "" : "s"} in progress` : "no runs in progress";
  const inboxPhrase = inboxCount > 0 ? `${inboxCount} inbox item${inboxCount === 1 ? "" : "s"} waiting on you` : "inbox is clear";
  return `Everything's healthy across ${workspaces.length} workspace${workspaces.length === 1 ? "" : "s"} — ${runsPhrase}, ${inboxPhrase}.`;
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

function mergeHeaders(headers: HeadersInit | undefined): Record<string, string> {
  if (!headers) return {};
  if (Array.isArray(headers)) {
    return Object.fromEntries(headers.map(([key, value]) => [key, value]));
  }
  if (typeof Headers !== "undefined" && headers instanceof Headers) {
    const merged: Record<string, string> = {};
    headers.forEach((value, key) => {
      merged[key] = value;
    });
    return merged;
  }
  return { ...(headers as Record<string, string>) };
}

async function fetchJson(path: string, init?: RequestInit, operatorToken = "", sessionToken = ""): Promise<unknown> {
  const token = operatorToken.trim();
  const session = sessionToken.trim();
  const response = await fetch(`${CONTROL_PLANE_URL}${path}`, {
    ...init,
    credentials: init?.credentials ?? "include",
    headers: {
      Accept: "application/json",
      ...(init?.body ? { "Content-Type": "application/json" } : {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(session ? { "x-axon-desktop-session": session } : {}),
      ...mergeHeaders(init?.headers),
    },
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

/**
 * Case-insensitive match against label and workspace_id, order-preserving.
 * Pure and exported-shape so it stays easy to reason about even though this
 * app has no test harness (no jest/testing-library in package.json) to pin
 * it down with an actual test.
 */
function filterWorkspaces(
  workspaces: Record<string, unknown>[],
  query: string,
): Record<string, unknown>[] {
  const needle = query.trim().toLowerCase();
  if (!needle) return workspaces;
  return workspaces.filter((workspace) => {
    const label = workspaceLabel(workspace).toLowerCase();
    const id = typeof workspace.workspace_id === "string" ? workspace.workspace_id.toLowerCase() : "";
    return label.includes(needle) || id.includes(needle);
  });
}

const RUNS_NEEDING_ATTENTION_PHASES = new Set(["failed", "awaiting_approval"]);

/**
 * The subset of runs worth showing an operator by default: failed or waiting
 * on their approval, newest first. /api/runs returns full history (verified
 * live: 583 records across this fleet) -- rendering that unfiltered would
 * bury the two or three that actually need a human behind hundreds of
 * long-settled "completed" rows.
 */
function runsNeedingAttention(runs: Record<string, unknown>[]): Record<string, unknown>[] {
  return runs
    .filter((run) => RUNS_NEEDING_ATTENTION_PHASES.has(String(run.phase ?? "")))
    .sort((a, b) => String(b.updated_at ?? "").localeCompare(String(a.updated_at ?? "")));
}

function employeeSummary(employee: Record<string, unknown>): string {
  const role = typeof employee.role_label === "string" ? employee.role_label : typeof employee.role === "string" ? employee.role : "Employee";
  const status = typeof employee.status === "string" ? employee.status.replace(/_/g, " ") : "idle";
  const owns = typeof employee.owns === "string" ? employee.owns : "";
  return owns ? `${role} · ${status} · ${owns}` : `${role} · ${status}`;
}

function actionAvailability(run: Record<string, unknown> | null): RunActionAvailability {
  return {
    approve: Boolean(run?.can_approve),
    reject: Boolean(run?.can_approve),
    resume: Boolean(run?.can_resume),
    stop: Boolean(run?.can_stop),
  };
}

function runPhase(record: Record<string, unknown> | null): string {
  if (!record) return "standby";
  return typeof record.phase === "string" && record.phase.trim() ? record.phase : "active";
}

function runIdentifier(record: Record<string, unknown> | null): string {
  if (!record) return "No run";
  if (typeof record.run_id === "string" && record.run_id.trim()) return record.run_id;
  if (typeof record.id === "string" && record.id.trim()) return record.id;
  return "run";
}

function runSummary(record: Record<string, unknown> | null): string {
  if (!record) return "No active run is available for the selected workspace.";
  if (typeof record.summary === "string" && record.summary.trim()) return record.summary;
  if (typeof record.title === "string" && record.title.trim()) return record.title;
  return `Run phase: ${runPhase(record)}`;
}

function readableWorkspaceId(workspaceId: string | null): string {
  if (!workspaceId) return "No target";
  return workspaceId.replace(/^workspace_/, "").replace(/_/g, " ");
}

function buildVaxonAdvisory(
  failures: Failures,
  focusCard: FocusCard,
  topRun: Record<string, unknown> | null,
): VaxonAdvisory {
  if (failures.health || failures.runtime) {
    return {
      title: "Control-plane link degraded",
      detail: failures.health ?? failures.runtime ?? "One of the live control surfaces is offline.",
      tone: "error",
      intent: "Restore telemetry before issuing broad commands.",
    };
  }

  const phase = runPhase(topRun);
  if (phase === "failed") {
    return {
      title: "Failed run needs triage",
      detail: runSummary(topRun),
      tone: "error",
      intent: "Inspect receipts, fix the cause, then retry only from a clean state.",
    };
  }

  if (phase === "awaiting_approval") {
    return {
      title: "Decision gate waiting",
      detail: runSummary(topRun),
      tone: "warn",
      intent: "Approve or reject from Command after checking the briefing.",
    };
  }

  if (focusCard.tone === "warn") {
    return {
      title: focusCard.title,
      detail: focusCard.detail,
      tone: "warn",
      intent: "Clear the highest-attention item before starting another run.",
    };
  }

  if (!topRun) {
    return {
      title: "No active run selected",
      detail: "Choose a workspace and start a scoped run when you are ready.",
      tone: "neutral",
      intent: "Hold standby until the operator defines the next mission.",
    };
  }

  return {
    title: "Autonomy nominal",
    detail: runSummary(topRun),
    tone: "ok",
    intent: "Keep observing. Command controls are armed for the selected workspace.",
  };
}

function buildAttentionScore(
  topStats: SummaryStat[],
  failures: Failures,
  topRun: Record<string, unknown> | null,
): number {
  const errorStats = topStats.filter((stat) => stat.tone === "error").length;
  const warnStats = topStats.filter((stat) => stat.tone === "warn").length;
  const phase = runPhase(topRun);
  const phasePenalty = phase === "failed" ? 22 : phase === "awaiting_approval" ? 10 : 0;
  return Math.max(0, Math.min(100, 100 - errorStats * 14 - warnStats * 7 - Object.keys(failures).length * 10 - phasePenalty));
}

const LIVE_EVENTS_PATH = "/api/live/events";
const LIVE_EVENTS_MIN_RETRY_MS = 1000;
const LIVE_EVENTS_MAX_RETRY_MS = 30000;
const LIVE_EVENTS_DEBOUNCE_MS = 300;

/**
 * SSE client for /api/live/events, built on XMLHttpRequest rather than the
 * EventSource API -- React Native / Hermes has no native EventSource, and a
 * hand-rolled parser over XHR's incremental responseText avoids adding a new
 * native dependency this close to an EAS build (a new native module would
 * need to be verified against the actual device build, which nothing in this
 * environment can do).
 *
 * The server's own comment on broadcast_material_change calls it
 * "event-driven proactive invalidation, not a timer heartbeat" -- real state
 * changes arrive as a distinct `material_change`/`spoken_line` event, while
 * `runtime_refresh`/`presence_refresh` are periodic housekeeping ticks the
 * server already sends every 30s/60s. This client does not need to tell them
 * apart: any parsed frame after the initial `connected` ack triggers a
 * debounced refresh, so a real change refreshes near-instantly and the
 * periodic ticks act as a safety-net fallback if a change event is ever
 * missed.
 */
function useLiveEvents(refreshRef: { current: () => void }, onConnectedChange: (connected: boolean) => void): void {
  useEffect(() => {
    let cancelled = false;
    let xhr: XMLHttpRequest | null = null;
    let retryTimer: ReturnType<typeof setTimeout> | null = null;
    let debounceTimer: ReturnType<typeof setTimeout> | null = null;
    let retryDelay = LIVE_EVENTS_MIN_RETRY_MS;
    let sawFirstFrame = false;

    function scheduleRefresh() {
      if (debounceTimer) clearTimeout(debounceTimer);
      debounceTimer = setTimeout(() => {
        refreshRef.current();
      }, LIVE_EVENTS_DEBOUNCE_MS);
    }

    function connect() {
      if (cancelled) return;
      let lastLength = 0;
      sawFirstFrame = false;
      const request = new XMLHttpRequest();
      xhr = request;
      request.open("GET", `${CONTROL_PLANE_URL}${LIVE_EVENTS_PATH}`, true);

      request.onreadystatechange = () => {
        if (cancelled) return;
        // HEADERS_RECEIVED (2) or later with a 200 is the closest signal RN's
        // XHR polyfill gives for "the connection is actually open" ahead of
        // any SSE frame arriving.
        if (request.readyState >= 2 && request.status === 200) {
          onConnectedChange(true);
          retryDelay = LIVE_EVENTS_MIN_RETRY_MS;
        }
      };

      request.onprogress = () => {
        if (cancelled) return;
        const text = request.responseText || "";
        if (text.length <= lastLength) return;
        lastLength = text.length;
        if (!sawFirstFrame) {
          // Skip the initial `data: {"type":"connected"}` ack -- there is
          // nothing new to refresh yet, it only confirms the stream is live.
          sawFirstFrame = true;
          return;
        }
        scheduleRefresh();
      };

      // XHR fires both `error` and `loadend` for a single network failure.
      // Without this guard, handleClose ran twice per disconnect and
      // scheduled two reconnects -- which compounds into more and more
      // overlapping live-event connections on every subsequent retry.
      let closed = false;
      const handleClose = () => {
        if (cancelled || closed) return;
        closed = true;
        onConnectedChange(false);
        xhr = null;
        retryTimer = setTimeout(connect, retryDelay);
        retryDelay = Math.min(retryDelay * 2, LIVE_EVENTS_MAX_RETRY_MS);
      };
      request.onerror = handleClose;
      request.onloadend = handleClose;

      request.send();
    }

    connect();

    return () => {
      cancelled = true;
      onConnectedChange(false);
      if (retryTimer) clearTimeout(retryTimer);
      if (debounceTimer) clearTimeout(debounceTimer);
      xhr?.abort();
    };
    // Intentionally mount-once: refreshRef and onConnectedChange are stable
    // (a ref object and a useState setter), so the stream must not
    // reconnect just because the workspace selection changed.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
}

export default function App() {
  const [active, setActive] = useState<SurfaceKey>("health");
  const [cockpitMode, setCockpitMode] = useState<CockpitMode>("overview");
  const [snapshot, setSnapshot] = useState<Snapshot>({});
  const [failures, setFailures] = useState<Failures>({});
  const [refreshing, setRefreshing] = useState(false);
  const [updatedAt, setUpdatedAt] = useState<Date | null>(null);
  const [selectedWorkspaceId, setSelectedWorkspaceId] = useState<string | null>(null);
  // The horizontal chip row only ever showed the first ~3 workspaces on
  // screen at once with no way to jump directly to one further down; this
  // repo already has 18 registered. The modal below adds search on top of
  // the same chip row rather than replacing it, so one-tap recents still work.
  const [workspacePickerOpen, setWorkspacePickerOpen] = useState(false);
  const [workspaceSearchQuery, setWorkspaceSearchQuery] = useState("");
  // Stat tiles (Health/Runtime/Runs/Workspaces/Leads/Inbox) were plain Views
  // with no onPress -- tapping any of them did nothing, and there was no way
  // to see *which* workspace's run failed beyond a single "Top run" card.
  // /api/runs alone returns 583 historical records across the whole fleet
  // (verified live), so "Runs" opens a browser pre-filtered to
  // failed/awaiting_approval and sorted by recency, not a dump of everything.
  const [runsBrowserOpen, setRunsBrowserOpen] = useState(false);
  const [inboxBrowserOpen, setInboxBrowserOpen] = useState(false);
  const [operatorSession, setOperatorSession] = useState<OperatorSessionStatus | null>(null);
  const [operatorToken, setOperatorToken] = useState("");
  const [operatorSessionToken, setOperatorSessionToken] = useState("");
  const [operatorPasswordDraft, setOperatorPasswordDraft] = useState("");
  const [showOperatorPassword, setShowOperatorPassword] = useState(false);
  const [authStatusMessage, setAuthStatusMessage] = useState("");
  const [authWorking, setAuthWorking] = useState(false);
  const [workspaceCompany, setWorkspaceCompany] = useState<unknown>(null);
  const [workspaceCompanyError, setWorkspaceCompanyError] = useState<string | null>(null);
  const [actionState, setActionState] = useState<ActionState>({ kind: "idle", message: "" });
  const [composerText, setComposerText] = useState("REPORT: brief me on attention, active runs, and next move.");
  const [commandHistory, setCommandHistory] = useState<CommandEntry[]>([]);
  const [voiceState, setVoiceState] = useState<VoiceState>("idle");
  const [voiceMessage, setVoiceMessage] = useState("");
  const [voiceTranscript, setVoiceTranscript] = useState("");
  const voiceRecognitionRef = useRef<SpeechRecognitionLike | null>(null);
  const voiceHandledRef = useRef(false);

  const checkOperatorSession = useCallback(async (
    token = operatorToken,
    sessionToken = operatorSessionToken,
  ): Promise<OperatorSessionStatus | null> => {
    try {
      const data = await fetchJson("/api/auth/session", undefined, token, sessionToken) as OperatorSessionStatus;
      setOperatorSession(data);
      if (data.authenticated || data.auth_required === false) {
        setAuthStatusMessage(`Operator access ready (${data.identity ?? "session"}).`);
      } else {
        setAuthStatusMessage("Operator password required before command dispatch.");
      }
      return data;
    } catch (error) {
      const message = error instanceof Error ? error.message : "Request failed";
      setOperatorSession(null);
      setAuthStatusMessage(explainFetchFailure(message, CONTROL_PLANE_URL));
      return null;
    }
  }, [operatorSessionToken, operatorToken]);

  const refresh = useCallback(async () => {
    setRefreshing(true);
    try {
      const results = await Promise.all(
        SURFACES.map(async (surface) => {
          try {
            return {
              key: surface.key,
              data: await fetchJson(surfacePath(surface, selectedWorkspaceId), undefined, operatorToken, operatorSessionToken),
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
  }, [operatorSessionToken, operatorToken, selectedWorkspaceId]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  // Always call the latest refresh without re-opening the SSE connection
  // every time selectedWorkspaceId/tokens change refresh's identity -- the
  // stream should stay open across workspace switches, not reconnect.
  const refreshRef = useRef(refresh);
  useEffect(() => {
    refreshRef.current = refresh;
  }, [refresh]);
  const [liveConnected, setLiveConnected] = useState(false);
  useLiveEvents(refreshRef, setLiveConnected);

  useEffect(() => {
    void checkOperatorSession();
  }, [checkOperatorSession]);

  useEffect(() => {
    return () => {
      const recognition = voiceRecognitionRef.current;
      voiceRecognitionRef.current = null;
      try {
        recognition?.abort?.();
      } catch {
        // SpeechRecognition abort can throw after the session already ended.
      }
    };
  }, []);

  useEffect(() => {
    if (!selectedWorkspaceId) {
      setWorkspaceCompany(null);
      setWorkspaceCompanyError(null);
      return;
    }

    let cancelled = false;
    void (async () => {
      try {
        const data = await fetchJson(
          `/api/workspaces/${encodeURIComponent(selectedWorkspaceId)}/company`,
          undefined,
          operatorToken,
          operatorSessionToken,
        );
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
  }, [operatorSessionToken, operatorToken, selectedWorkspaceId, updatedAt]);

  const selected = useMemo(
    () => SURFACES.find((surface) => surface.key === active) ?? SURFACES[0],
    [active],
  );
  const selectedError = failures[active];
  const topStats = useMemo(
    () => buildTopStats(snapshot, failures, selectedWorkspaceId),
    [snapshot, failures, selectedWorkspaceId],
  );
  const situationSummary = useMemo(
    () => buildSituationSummary(snapshot, failures, selectedWorkspaceId),
    [snapshot, failures, selectedWorkspaceId],
  );
  // Fleet-wide (not filtered to selectedWorkspaceId) -- this is what actually
  // answers "which workspace's run failed", not just the one currently picked.
  const attentionRuns = useMemo(
    () => runsNeedingAttention(collectRunItems(snapshot, null)),
    [snapshot],
  );
  const inboxItems = useMemo(() => collectInboxItems(snapshot), [snapshot]);

  function jumpToRun(run: Record<string, unknown>): void {
    const runWorkspaceId = typeof run.workspace_id === "string" ? run.workspace_id : null;
    if (runWorkspaceId) setSelectedWorkspaceId(runWorkspaceId);
    setRunsBrowserOpen(false);
    setCockpitMode("overview");
  }

  function jumpToSignal(signal: Record<string, unknown>): void {
    const signalWorkspaceId = typeof signal.workspace_id === "string" ? signal.workspace_id : null;
    if (signalWorkspaceId) setSelectedWorkspaceId(signalWorkspaceId);
    setInboxBrowserOpen(false);
    setCockpitMode("overview");
  }
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
  const availableActions = useMemo(() => actionAvailability(topRun), [topRun]);
  const companyRecord = asRecord(workspaceCompany);
  const company = asRecord(companyRecord?.company);
  const employees = company ? (asArray(company.employees) as Record<string, unknown>[]) : [];
  const advisory = useMemo(() => buildVaxonAdvisory(failures, focusCard, topRun), [failures, focusCard, topRun]);
  const attentionScore = useMemo(
    () => buildAttentionScore(topStats, failures, topRun),
    [topStats, failures, topRun],
  );
  const failureCount = Object.keys(failures).length;
  const targetLabel = readableWorkspaceId(selectedWorkspaceId);
  const topRunPhase = runPhase(topRun);
  const topRunId = runIdentifier(topRun);
  const topRunCanAct = typeof topRun?.run_id === "string";
  const voiceSupported = speechRecognitionConstructor() !== null;
  const voiceStatus = voiceStateCopy(voiceState, voiceMessage);
  const operatorAccessReady = operatorSession?.authenticated === true || operatorSession?.auth_required === false;
  const operatorAccessRequired = operatorSession?.auth_required !== false;
  const operatorAccessBadge = operatorSession ? (operatorAccessReady ? "READY" : "LOCKED") : "CHECKING";
  const operatorAccessCopy = operatorAccessReady
    ? "Commands are unlocked for this mobile session."
    : operatorSession?.password_enabled === false
      ? "Password sign-in is not configured on the control plane yet. Set AXON_WATCH_OPERATOR_PASSWORD and restart CP."
    : operatorAccessRequired
      ? "Sign in with the operator password before creating, approving, resuming, or stopping runs."
      : "Local command dispatch is open for this control-plane mode.";
  const advisoryMode: CockpitMode =
    advisory.tone === "error" && (failures.health || failures.runtime || failureCount > 0)
      ? "data"
      : topRunPhase === "awaiting_approval" || !topRun
        ? "command"
        : "overview";

  const submitCommand = useCallback(
    async (source: CommandSource, overrideText?: string): Promise<boolean> => {
      const command = (overrideText ?? composerText).trim();
      if (!command) {
        setActionState({ kind: "error", message: "Write or speak a command before sending." });
        return false;
      }
      if (!selectedWorkspaceId) {
        setActionState({ kind: "error", message: "Select a workspace before sending VAXON a command." });
        return false;
      }
      if (operatorAccessRequired && !operatorAccessReady) {
        setActionState({
          kind: "error",
          message: operatorSession
            ? "Unlock operator access before sending commands. Enter the operator password in Operator access."
            : "Operator access is still being checked. Wait a moment, then unlock commands if prompted.",
        });
        return false;
      }

      const entryId = commandEntryId();
      const summary = command.replace(/\s+/g, " ").slice(0, 96);
      const detail = [
        `${commandTitle(source)} from Axon-X mobile control-plane.`,
        `Target workspace: ${selectedWorkspaceId}`,
        "",
        command,
      ].join("\n");

      const queuedEntry: CommandEntry = {
        id: entryId,
        source,
        status: "queued",
        text: command,
        time: new Date(),
        response: "Queued for control-plane dispatch.",
      };
      setCommandHistory((current) => [queuedEntry, ...current].slice(0, 8));
      setActionState({ kind: "working", message: `Sending ${commandTitle(source).toLowerCase()} to ${selectedWorkspaceId}...` });

      try {
        await fetchJson("/api/runs", {
          method: "POST",
          body: JSON.stringify({
            workspace_id: selectedWorkspaceId,
            summary,
            detail,
            mode: "agent",
          }),
        }, operatorToken, operatorSessionToken);
        setCommandHistory((current) =>
          current.map((entry) =>
            entry.id === entryId
              ? { ...entry, status: "sent", response: "Run created. Refreshing live state." }
              : entry,
          ),
        );
        setActionState({ kind: "success", message: `VAXON command sent to ${selectedWorkspaceId}.` });
        if (overrideText === undefined) setComposerText("");
        await refresh();
        return true;
      } catch (error) {
        const message = error instanceof Error ? error.message : "Request failed";
        const explained = explainFetchFailure(message, CONTROL_PLANE_URL);
        setCommandHistory((current) =>
          current.map((entry) =>
            entry.id === entryId
              ? { ...entry, status: "failed", response: explained }
              : entry,
          ),
        );
        setActionState({ kind: "error", message: explained });
        return false;
      }
    },
    [composerText, operatorAccessReady, operatorAccessRequired, operatorSession, operatorSessionToken, operatorToken, refresh, selectedWorkspaceId],
  );

  const runAction = useCallback(
    async (action: RunAction) => {
      if (!topRun || typeof topRun.run_id !== "string") return;
      if (operatorAccessRequired && !operatorAccessReady) {
        setActionState({
          kind: "error",
          message: "Unlock operator access before changing a run state.",
        });
        return;
      }
      setActionState({ kind: "working", message: `${action}ing ${topRun.run_id}...` });
      try {
        await fetchJson(`/api/runs/${encodeURIComponent(topRun.run_id)}/${action}`, { method: "POST" }, operatorToken, operatorSessionToken);
        setActionState({ kind: "success", message: `${action}ed ${topRun.run_id}.` });
        await refresh();
      } catch (error) {
        const message = error instanceof Error ? error.message : "Request failed";
        setActionState({ kind: "error", message: explainFetchFailure(message, CONTROL_PLANE_URL) });
      }
    },
    [operatorAccessReady, operatorAccessRequired, operatorSessionToken, operatorToken, refresh, topRun],
  );

  const startVoiceCommand = useCallback(() => {
    if (actionState.kind === "working") return;
    const Recognition = speechRecognitionConstructor();
    if (!Recognition) {
      setVoiceState("unavailable");
      setVoiceMessage("");
      return;
    }

    const recognition = new Recognition();
    voiceRecognitionRef.current = recognition;
    voiceHandledRef.current = false;
    setVoiceTranscript("");
    setVoiceMessage("");
    setVoiceState("listening");

    recognition.lang = "en-US";
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;
    recognition.onresult = (event) => {
      const transcript = Array.from(event.results ?? [])
        .map((result) => result[0]?.transcript ?? "")
        .join(" ")
        .trim();
      if (!transcript) {
        setVoiceState("failure");
        setVoiceMessage("No speech transcript was returned.");
        voiceHandledRef.current = true;
        return;
      }
      voiceHandledRef.current = true;
      setVoiceTranscript(transcript);
      setVoiceState("processing");
      setVoiceMessage("Transcription captured. Dispatching command.");
      void submitCommand("voice", transcript).then((ok) => {
        setVoiceState(ok ? "success" : "failure");
        setVoiceMessage(ok ? "Voice command dispatched." : "Voice command could not be dispatched.");
      });
    };
    recognition.onerror = (event) => {
      voiceHandledRef.current = true;
      const error = String(event.error || event.message || "speech recognition failed");
      if (error === "not-allowed" || error === "service-not-allowed") {
        setVoiceState("permission_denied");
        setVoiceMessage("");
      } else {
        setVoiceState("failure");
        setVoiceMessage(error);
      }
    };
    recognition.onend = () => {
      voiceRecognitionRef.current = null;
      if (!voiceHandledRef.current) {
        setVoiceState("failure");
        setVoiceMessage("Listening ended before a command was captured.");
      }
    };

    try {
      recognition.start();
    } catch (error) {
      voiceRecognitionRef.current = null;
      voiceHandledRef.current = true;
      setVoiceState("failure");
      setVoiceMessage(error instanceof Error ? error.message : "Could not start microphone capture.");
    }
  }, [actionState.kind, submitCommand]);

  const stopVoiceCommand = useCallback(() => {
    const recognition = voiceRecognitionRef.current;
    if (!recognition) return;
    voiceHandledRef.current = true;
    setVoiceState("processing");
    setVoiceMessage("Stopping microphone capture.");
    try {
      recognition.stop();
    } catch (error) {
      setVoiceState("failure");
      setVoiceMessage(error instanceof Error ? error.message : "Could not stop microphone capture.");
    }
  }, []);

  const unlockOperatorAccess = useCallback(async () => {
    const password = operatorPasswordDraft.trim();
    if (!password) {
      setAuthStatusMessage("Enter the operator password before unlocking commands.");
      return;
    }
    setAuthWorking(true);
    try {
      const session = await fetchJson(
        "/api/auth/session",
        {
          method: "POST",
          body: JSON.stringify({
            operator_password: password,
            operator_token: password,
            return_session_token: true,
          }),
        },
      ) as OperatorSessionStatus;
      if (!session || (!session.authenticated && session.auth_required !== false)) {
        setOperatorToken("");
        setOperatorSessionToken("");
        setAuthStatusMessage("That operator password was not accepted by the control plane.");
        return;
      }
      setOperatorToken("");
      setOperatorSessionToken(session.session_token ?? "");
      setOperatorPasswordDraft("");
      setOperatorSession(session);
      setAuthStatusMessage(`Operator access ready (${session.identity ?? "session"}).`);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Request failed";
      setOperatorToken("");
      setOperatorSessionToken("");
      setOperatorSession(null);
      setAuthStatusMessage(
        operatorSession?.password_enabled === false
          ? "Password sign-in is not configured on the control plane yet."
          : message.includes("invalid operator credentials")
          ? "That operator password was not accepted by the control plane."
          : explainFetchFailure(message, CONTROL_PLANE_URL),
      );
    } finally {
      setAuthWorking(false);
    }
  }, [operatorPasswordDraft, operatorSession]);

  const forgetOperatorAccess = useCallback(async () => {
    const token = operatorToken;
    setOperatorToken("");
    const sessionToken = operatorSessionToken;
    setOperatorSessionToken("");
    setOperatorPasswordDraft("");
    setShowOperatorPassword(false);
    setOperatorSession(null);
    setAuthStatusMessage("Operator session cleared from this mobile cockpit.");
    try {
      await fetchJson("/api/auth/session", { method: "DELETE" }, token, sessionToken);
    } catch {
      // Clearing the in-memory session is enough for mobile access.
    }
    void checkOperatorSession("", "");
  }, [checkOperatorSession, operatorSessionToken, operatorToken]);

  return (
    <SafeAreaView style={styles.safeArea}>
      <StatusBar style="light" />
      <ScrollView
        contentContainerStyle={styles.page}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={refresh} tintColor="#69f7f0" />}
      >
        <View style={styles.header}>
          <View style={styles.brandBlock}>
            <Text style={styles.eyebrow}>AXON-X</Text>
            <Text style={styles.title}>VAXON Cockpit</Text>
          </View>
          <View style={[styles.badge, toneStyle(advisory.tone)]}>
            <Text style={styles.badgeText}>{advisory.tone === "ok" ? "NOMINAL" : advisory.tone === "error" ? "ALERT" : "WATCH"}</Text>
          </View>
        </View>

        <View style={styles.liveRow}>
          <View style={[styles.liveDot, liveConnected ? styles.liveDotOn : styles.liveDotOff]} />
          <Text style={styles.liveLabel}>{liveConnected ? "LIVE" : "RECONNECTING"}</Text>
        </View>

        <Text numberOfLines={1} style={styles.endpoint}>
          {CONTROL_PLANE_URL}
        </Text>

        <View style={styles.heroCard}>
          <View style={styles.holoLineTop} />
          <View style={styles.holoLineBottom} />
          <View style={styles.heroHeader}>
            <View style={styles.panelHeaderCopy}>
              <Text style={styles.heroEyebrow}>Command core</Text>
              <Text numberOfLines={1} style={styles.heroTime}>{targetLabel}</Text>
            </View>
            <View style={styles.scoreRing}>
              <Text style={styles.scoreValue}>{attentionScore}</Text>
              <Text style={styles.scoreLabel}>SYNC</Text>
            </View>
          </View>

          <View style={styles.commandStage}>
            <View style={styles.vaxonOrb}>
              <View style={styles.orbPingOne} />
              <View style={styles.orbPingTwo} />
              <View style={styles.orbAxisVertical} />
              <View style={styles.orbAxisHorizontal} />
              <View style={styles.vaxonOrbOuter}>
                <Image source={vaxonOrbCinematic} style={styles.vaxonOrbImage} resizeMode="cover" />
                <View style={styles.orbGlassRing} />
                <View style={styles.orbCorePulse}>
                  <Text style={styles.orbCoreText}>VX</Text>
                </View>
              </View>
              <View style={[styles.orbNode, styles.orbNodeTop]} />
              <View style={[styles.orbNode, styles.orbNodeRight]} />
              <View style={[styles.orbNode, styles.orbNodeBottom]} />
              <View style={[styles.orbNode, styles.orbNodeLeft]} />
            </View>
            {/* These reflect VAXON's current state (voice capture / processing / advisory
                tone) -- they weren't buttons and had no onPress, which read as three dead
                controls. All three now jump to Command, where voice input and run actions
                actually live, rather than staying inert status text shaped like buttons. */}
            <View style={styles.orbStateRail}>
              <Pressable
                accessibilityRole="button"
                accessibilityLabel="Open Command to talk to VAXON"
                onPress={() => setCockpitMode("command")}
                style={[styles.orbStatePill, voiceState === "listening" && styles.orbStatePillActive]}
              >
                <Text style={styles.orbStatePillText}>Listen</Text>
              </Pressable>
              <Pressable
                accessibilityRole="button"
                accessibilityLabel="Open Command to see what VAXON is doing"
                onPress={() => setCockpitMode("command")}
                style={[styles.orbStatePill, actionState.kind === "working" && styles.orbStatePillActive]}
              >
                <Text style={styles.orbStatePillText}>Think</Text>
              </Pressable>
              <Pressable
                accessibilityRole="button"
                accessibilityLabel="Open Command to act on the current run"
                onPress={() => setCockpitMode("command")}
                style={[styles.orbStatePill, advisory.tone === "ok" && styles.orbStatePillActive]}
              >
                <Text style={styles.orbStatePillText}>Act</Text>
              </Pressable>
            </View>

            <View style={styles.advisoryPanel}>
              <View style={styles.advisoryHeader}>
                <View style={[styles.statDot, toneStyle(advisory.tone)]} />
                <Text style={styles.advisoryLabel}>VAXON advisory</Text>
              </View>
              <Text numberOfLines={2} style={styles.heroTitle}>{advisory.title}</Text>
              <Text style={styles.heroBody}>{advisory.detail}</Text>
              <Text style={styles.heroIntent}>{advisory.intent}</Text>
              <Pressable
                accessibilityRole="button"
                onPress={() => setCockpitMode(advisoryMode)}
                style={styles.commandShortcut}
              >
                <Text style={styles.commandShortcutText}>OPEN {advisoryMode.toUpperCase()}</Text>
              </Pressable>
            </View>
          </View>

          <View style={styles.telemetryRail}>
            <View style={styles.telemetryCell}>
              <Text style={styles.telemetryLabel}>Run</Text>
              <Text numberOfLines={1} style={styles.telemetryValue}>{topRunId}</Text>
            </View>
            <View style={styles.telemetryCell}>
              <Text style={styles.telemetryLabel}>Phase</Text>
              <Text numberOfLines={1} style={styles.telemetryValue}>{topRunPhase}</Text>
            </View>
            <View style={styles.telemetryCell}>
              <Text style={styles.telemetryLabel}>Faults</Text>
              <Text style={styles.telemetryValue}>{failureCount}</Text>
            </View>
            <View style={styles.telemetryCell}>
              <Text style={styles.telemetryLabel}>Last</Text>
              <Text style={styles.telemetryValue}>{formatClock(updatedAt)}</Text>
            </View>
          </View>
        </View>

        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.modeRail}>
          {COCKPIT_MODES.map((mode) => {
            const selectedMode = mode.key === cockpitMode;
            return (
              <Pressable
                key={mode.key}
                accessibilityRole="button"
                accessibilityState={{ selected: selectedMode }}
                onPress={() => setCockpitMode(mode.key)}
                style={[styles.modePill, selectedMode && styles.modePillActive]}
              >
                <Text numberOfLines={1} style={[styles.modeEyebrow, selectedMode && styles.modeEyebrowActive]}>{mode.eyebrow}</Text>
                <Text numberOfLines={1} style={[styles.modeLabel, selectedMode && styles.modeLabelActive]}>{mode.label}</Text>
              </Pressable>
            );
          })}
        </ScrollView>

        {cockpitMode === "overview" ? (
          <View style={styles.modeDeck}>
            <View style={styles.sectionHeader}>
              <Text style={styles.sectionKicker}>Live picture</Text>
              <Text style={styles.sectionTitle}>Workspace state</Text>
            </View>
            <Text style={styles.situationSummary}>{situationSummary}</Text>
            <View style={styles.statsRow}>
              {topStats.map((stat) => {
                const action = STAT_TILE_ACTIONS[stat.label];
                return (
                  <Pressable
                    key={stat.label}
                    accessibilityRole={action ? "button" : undefined}
                    disabled={!action}
                    onPress={() => {
                      if (action === "runs") setRunsBrowserOpen(true);
                      else if (action === "inbox") setInboxBrowserOpen(true);
                      else if (action === "workspaces") setWorkspacePickerOpen(true);
                      else if (action === "fleet") setCockpitMode("fleet");
                      else if (action === "data") setCockpitMode("data");
                    }}
                    style={({ pressed }) => [styles.statCard, action && pressed && styles.statCardPressed]}
                  >
                    <View style={styles.statCardHeader}>
                      <View style={[styles.statDot, toneStyle(stat.tone ?? "neutral")]} />
                      {action ? <Text style={styles.statCardChevron}>›</Text> : null}
                    </View>
                    <Text style={styles.statLabel}>{stat.label}</Text>
                    <Text numberOfLines={1} style={styles.statValue}>{stat.value}</Text>
                  </Pressable>
                );
              })}
            </View>
            <View style={styles.focusRow}>
              <View style={styles.focusPanel}>
                <Text style={styles.focusLabel}>Top run</Text>
                <Text numberOfLines={2} style={styles.focusTitle}>{runCard.title}</Text>
                <Text style={styles.focusBody}>{runCard.detail}</Text>
              </View>
              <View style={styles.focusPanel}>
                <Text style={styles.focusLabel}>Briefing</Text>
                <Text numberOfLines={2} style={styles.focusTitle}>{focusCard.title}</Text>
                <Text style={styles.focusBody}>{focusCard.detail}</Text>
              </View>
            </View>
          </View>
        ) : null}

        {cockpitMode === "command" ? (
          <View style={styles.modeDeck}>
            <View style={styles.panel}>
              <View style={styles.panelHeader}>
                <Text style={styles.panelTitle}>Target workspace</Text>
                <Pressable
                  accessibilityRole="button"
                  accessibilityLabel={`Search all ${workspaces.length} workspaces`}
                  onPress={() => setWorkspacePickerOpen(true)}
                  style={styles.workspaceSearchTrigger}
                >
                  <Text style={styles.workspaceSearchTriggerText}>
                    All ({workspaces.length})
                  </Text>
                </Pressable>
              </View>
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
                      <Text numberOfLines={1} style={[styles.chipText, selectedWorkspace && styles.chipTextActive]}>
                        {workspaceLabel(workspace)}
                      </Text>
                    </Pressable>
                  );
                })}
              </ScrollView>
              <Text numberOfLines={1} style={styles.panelMeta}>
                {selectedWorkspaceId ? `Targeting ${selectedWorkspaceId}` : "No workspace surfaced yet."}
              </Text>
            </View>

            <View style={styles.panel}>
              <View style={styles.panelHeader}>
                <View style={styles.panelHeaderCopy}>
                  <Text style={styles.panelTitle}>Operator access</Text>
                  <Text style={styles.panelCopy}>{operatorAccessCopy}</Text>
                </View>
                <View style={[styles.accessBadge, operatorAccessReady ? styles.accessBadgeReady : styles.accessBadgeLocked]}>
                  <Text style={styles.accessBadgeText}>{operatorAccessBadge}</Text>
                </View>
              </View>
              {operatorAccessRequired && !operatorAccessReady ? (
                <>
                  <View style={styles.passwordField}>
                    <TextInput
                      style={styles.passwordFieldInput}
                      value={operatorPasswordDraft}
                      onChangeText={setOperatorPasswordDraft}
                      placeholder="Operator password"
                      placeholderTextColor="#78918d"
                      secureTextEntry={!showOperatorPassword}
                      autoCapitalize="none"
                      autoCorrect={false}
                    />
                    <Pressable
                      accessibilityRole="button"
                      accessibilityLabel={showOperatorPassword ? "Hide operator password" : "Show operator password"}
                      onPress={() => setShowOperatorPassword((value) => !value)}
                      style={styles.passwordVisibilityButton}
                    >
                      <Text style={styles.passwordVisibilityText}>
                        {showOperatorPassword ? "HIDE" : "SHOW"}
                      </Text>
                    </Pressable>
                  </View>
                  <Pressable
                    accessibilityRole="button"
                    onPress={() => void unlockOperatorAccess()}
                    disabled={authWorking || !operatorPasswordDraft.trim()}
                    style={[styles.actionButton, (authWorking || !operatorPasswordDraft.trim()) && styles.actionButtonDisabled]}
                  >
                    <Text style={styles.actionButtonText}>{authWorking ? "Checking..." : "Unlock with password"}</Text>
                  </Pressable>
                </>
              ) : null}
              {operatorAccessRequired && operatorAccessReady ? (
                <Pressable
                  accessibilityRole="button"
                  onPress={() => void forgetOperatorAccess()}
                  style={[styles.actionButtonSecondary, styles.accessClearButton]}
                >
                  <Text style={styles.actionButtonText}>Lock cockpit</Text>
                </Pressable>
              ) : null}
              {authStatusMessage ? (
                <Text style={[styles.statusMessage, operatorAccessReady ? styles.statusSuccess : styles.statusError]}>
                  {authStatusMessage}
                </Text>
              ) : null}
            </View>

            <View style={styles.panel}>
              <View style={styles.panelHeader}>
                <View style={styles.panelHeaderCopy}>
                  <Text style={styles.panelTitle}>VAXON composer</Text>
                  <Text style={styles.panelCopy}>Type or speak one precise instruction. VAXON will create a scoped mobile run for the selected workspace.</Text>
                </View>
                {actionState.kind === "working" ? <ActivityIndicator color="#69f7f0" /> : null}
              </View>

              <View style={styles.voicePanel}>
                <View style={styles.voiceCopy}>
                  <Text style={styles.voiceLabel}>{voiceStateLabel(voiceState)}</Text>
                  <Text style={styles.voiceBody}>{voiceStatus}</Text>
                  {voiceTranscript ? <Text numberOfLines={2} style={styles.voiceTranscript}>{voiceTranscript}</Text> : null}
                </View>
                <Pressable
                  accessibilityRole="button"
                  onPress={voiceState === "listening" ? stopVoiceCommand : startVoiceCommand}
                  style={[
                    styles.micButton,
                    voiceState === "listening" && styles.micButtonLive,
                    !voiceSupported && styles.micButtonUnavailable,
                  ]}
                >
                  <Text style={styles.micButtonText}>{voiceState === "listening" ? "STOP" : "MIC"}</Text>
                </Pressable>
              </View>

              <View style={styles.quickCommandRow}>
                {QUICK_COMMANDS.map((command) => (
                  <Pressable
                    key={command}
                    accessibilityRole="button"
                    onPress={() => setComposerText(command)}
                    style={styles.quickCommand}
                  >
                    <Text numberOfLines={2} style={styles.quickCommandText}>{command}</Text>
                  </Pressable>
                ))}
              </View>

              <TextInput
                style={[styles.input, styles.composerInput]}
                value={composerText}
                onChangeText={setComposerText}
                placeholder="Ask VAXON for status, triage, recovery, routing, or a bounded action..."
                placeholderTextColor="#78918d"
                multiline
              />
              <Pressable
                accessibilityRole="button"
                onPress={() => void submitCommand("typed")}
                style={[styles.actionButton, (!selectedWorkspaceId || !composerText.trim() || actionState.kind === "working" || !operatorAccessReady) && styles.actionButtonDisabled]}
                disabled={!selectedWorkspaceId || !composerText.trim() || actionState.kind === "working" || !operatorAccessReady}
              >
                <Text style={styles.actionButtonText}>Send to VAXON</Text>
              </Pressable>
              <View style={styles.actionRow}>
                {(["approve", "reject", "resume", "stop"] as RunAction[]).map((action) => {
                  const disabled = !topRunCanAct || !availableActions[action] || actionState.kind === "working" || !operatorAccessReady;
                  return (
                    <Pressable
                      key={action}
                      accessibilityRole="button"
                      onPress={() => void runAction(action)}
                      style={[styles.actionButtonSecondary, disabled && styles.actionButtonDisabled]}
                      disabled={disabled}
                    >
                      <Text style={styles.actionButtonText}>{action.toUpperCase()}</Text>
                    </Pressable>
                  );
                })}
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
              <View style={styles.panelHeader}>
                <View style={styles.panelHeaderCopy}>
                  <Text style={styles.panelTitle}>Command feedback</Text>
                  <Text style={styles.panelCopy}>Recent mobile instructions stay visible so the cockpit feels continuous instead of fire-and-forget.</Text>
                </View>
              </View>
              {commandHistory.length > 0 ? (
                <View style={styles.commandHistoryList}>
                  {commandHistory.map((entry) => (
                    <View key={entry.id} style={styles.commandHistoryItem}>
                      <View style={styles.commandHistoryHeader}>
                        <Text style={styles.commandHistorySource}>{commandTitle(entry.source)}</Text>
                        <Text style={[
                          styles.commandHistoryStatus,
                          entry.status === "sent" ? styles.commandHistorySent : entry.status === "failed" ? styles.commandHistoryFailed : styles.commandHistoryQueued,
                        ]}>
                          {entry.status.toUpperCase()}
                        </Text>
                      </View>
                      <Text numberOfLines={2} style={styles.commandHistoryText}>{entry.text}</Text>
                      <Text numberOfLines={2} style={styles.commandHistoryResponse}>{entry.response}</Text>
                      <Text style={styles.commandHistoryTime}>{entry.time.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</Text>
                    </View>
                  ))}
                </View>
              ) : (
                <Text style={styles.panelMeta}>No mobile commands sent in this session yet.</Text>
              )}
            </View>
          </View>
        ) : null}

        {cockpitMode === "fleet" ? (
          <View style={styles.modeDeck}>
            <View style={styles.sectionHeader}>
              <Text style={styles.sectionKicker}>Human loop</Text>
              <Text style={styles.sectionTitle}>Workspace fleet</Text>
            </View>
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
                      <View style={styles.employeeAvatar}>
                        <Text style={styles.employeeAvatarText}>
                          {typeof employee.name === "string" && employee.name.trim() ? employee.name.trim().slice(0, 1) : "A"}
                        </Text>
                      </View>
                      <View style={styles.employeeCopy}>
                        <Text numberOfLines={1} style={styles.listTitle}>
                          {typeof employee.name === "string" ? employee.name : employeeId}
                        </Text>
                        <Text numberOfLines={2} style={styles.listDetail}>{employeeSummary(employee)}</Text>
                      </View>
                    </View>
                  );
                })}
              </View>
            ) : (
              <Text style={styles.panelMeta}>No roster is available for this workspace yet.</Text>
            )}
          </View>
        ) : null}

        {cockpitMode === "data" ? (
          <View style={styles.modeDeck}>
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
                    <Text style={[styles.tileLabel, isActive && styles.activeTileLabel]}>{surface.label}</Text>
                    <Text numberOfLines={1} style={styles.tileValue}>
                      {hasError ? "Unavailable" : summarizeSurface(snapshot[surface.key])}
                    </Text>
                  </Pressable>
                );
              })}
            </View>

            <View style={styles.panel}>
              <View style={styles.panelHeader}>
                <View style={styles.panelHeaderCopy}>
                  <Text style={styles.panelTitle}>{selected.label}</Text>
                  <Text numberOfLines={1} style={styles.path}>{surfacePath(selected, selectedWorkspaceId)}</Text>
                </View>
                {refreshing ? <ActivityIndicator color="#69f7f0" /> : null}
              </View>

              {selectedError ? (
                <View style={styles.errorPanel}>
                  <Text style={styles.errorTitle}>Unavailable</Text>
                  <Text style={styles.errorText}>{selectedError}</Text>
                  <Text style={styles.errorHint}>{surfaceErrorHint(CONTROL_PLANE_URL, selectedError)}</Text>
                </View>
              ) : (
                <ScrollView horizontal style={styles.payloadScroller}>
                  <Text selectable style={styles.payload}>
                    {compactJson(snapshot[active])}
                  </Text>
                </ScrollView>
              )}
            </View>
          </View>
        ) : null}

        {/* These three render regardless of the active cockpitMode tab: their
            triggers live on both the Overview stat tiles and, for the
            workspace picker, the Command tab's "All" button. A modal gated
            inside a single {cockpitMode === "..." ? ...} block only renders
            while that tab happens to be selected -- opening it from a
            different tab would silently do nothing, which was the exact bug
            being fixed here. */}
        <Modal
          visible={workspacePickerOpen}
          animationType="slide"
          transparent
          onRequestClose={() => {
            setWorkspacePickerOpen(false);
            setWorkspaceSearchQuery("");
          }}
        >
          <View style={styles.workspacePickerBackdrop}>
            <Pressable
              style={styles.workspacePickerBackdropTouch}
              accessibilityLabel="Close workspace search"
              onPress={() => {
                setWorkspacePickerOpen(false);
                setWorkspaceSearchQuery("");
              }}
            />
            <SafeAreaView style={styles.workspacePickerSheet}>
              <View style={styles.workspacePickerHeader}>
                <Text style={styles.panelTitle}>Workspaces</Text>
                <Pressable
                  accessibilityRole="button"
                  accessibilityLabel="Close"
                  onPress={() => {
                    setWorkspacePickerOpen(false);
                    setWorkspaceSearchQuery("");
                  }}
                >
                  <Text style={styles.workspacePickerClose}>Close</Text>
                </Pressable>
              </View>
              <TextInput
                value={workspaceSearchQuery}
                onChangeText={setWorkspaceSearchQuery}
                placeholder="Search by name or workspace_id..."
                placeholderTextColor="#5f8482"
                autoCapitalize="none"
                autoCorrect={false}
                style={styles.workspaceSearchInput}
              />
              <FlatList
                data={filterWorkspaces(workspaces, workspaceSearchQuery)}
                keyExtractor={(workspace) =>
                  typeof workspace.workspace_id === "string" ? workspace.workspace_id : recordId(workspace)
                }
                keyboardShouldPersistTaps="handled"
                ListEmptyComponent={
                  <Text style={styles.workspacePickerEmpty}>No workspace matches "{workspaceSearchQuery}".</Text>
                }
                renderItem={({ item: workspace }) => {
                  const workspaceId =
                    typeof workspace.workspace_id === "string" ? workspace.workspace_id : recordId(workspace);
                  const selectedWorkspace = workspaceId === selectedWorkspaceId;
                  return (
                    <Pressable
                      accessibilityRole="button"
                      accessibilityState={{ selected: selectedWorkspace }}
                      onPress={() => {
                        setSelectedWorkspaceId(workspaceId);
                        setWorkspacePickerOpen(false);
                        setWorkspaceSearchQuery("");
                      }}
                      style={[styles.workspacePickerRow, selectedWorkspace && styles.workspacePickerRowActive]}
                    >
                      <Text numberOfLines={1} style={styles.workspacePickerRowLabel}>
                        {workspaceLabel(workspace)}
                      </Text>
                      <Text numberOfLines={1} style={styles.workspacePickerRowId}>
                        {workspaceId}
                      </Text>
                    </Pressable>
                  );
                }}
              />
            </SafeAreaView>
          </View>
        </Modal>

        <Modal
          visible={runsBrowserOpen}
          animationType="slide"
          transparent
          onRequestClose={() => setRunsBrowserOpen(false)}
        >
          <View style={styles.workspacePickerBackdrop}>
            <Pressable
              style={styles.workspacePickerBackdropTouch}
              accessibilityLabel="Close runs needing attention"
              onPress={() => setRunsBrowserOpen(false)}
            />
            <SafeAreaView style={styles.workspacePickerSheet}>
              <View style={styles.workspacePickerHeader}>
                <Text style={styles.panelTitle}>Needs attention</Text>
                <Pressable
                  accessibilityRole="button"
                  accessibilityLabel="Close"
                  onPress={() => setRunsBrowserOpen(false)}
                >
                  <Text style={styles.workspacePickerClose}>Close</Text>
                </Pressable>
              </View>
              <Text style={styles.browserSubtitle}>
                Failed or awaiting your approval, across every workspace — newest first.
              </Text>
              <FlatList
                data={attentionRuns}
                keyExtractor={(run) => runIdentifier(run)}
                ListEmptyComponent={
                  <Text style={styles.workspacePickerEmpty}>Nothing needs attention right now.</Text>
                }
                renderItem={({ item: run }) => {
                  const phase = runPhase(run);
                  return (
                    <Pressable
                      accessibilityRole="button"
                      onPress={() => jumpToRun(run)}
                      style={styles.workspacePickerRow}
                    >
                      <View style={styles.browserRowHeader}>
                        <Text numberOfLines={1} style={styles.workspacePickerRowLabel}>
                          {readableWorkspaceId(typeof run.workspace_id === "string" ? run.workspace_id : null)}
                        </Text>
                        <View style={[styles.browserPhaseBadge, toneStyle(phase === "failed" ? "error" : "warn")]}>
                          <Text style={styles.browserPhaseBadgeText}>{phase.replace(/_/g, " ")}</Text>
                        </View>
                      </View>
                      <Text numberOfLines={1} style={styles.workspacePickerRowId}>{runIdentifier(run)}</Text>
                      <Text numberOfLines={2} style={styles.browserRowDetail}>{runSummary(run)}</Text>
                    </Pressable>
                  );
                }}
              />
            </SafeAreaView>
          </View>
        </Modal>

        <Modal
          visible={inboxBrowserOpen}
          animationType="slide"
          transparent
          onRequestClose={() => setInboxBrowserOpen(false)}
        >
          <View style={styles.workspacePickerBackdrop}>
            <Pressable
              style={styles.workspacePickerBackdropTouch}
              accessibilityLabel="Close inbox"
              onPress={() => setInboxBrowserOpen(false)}
            />
            <SafeAreaView style={styles.workspacePickerSheet}>
              <View style={styles.workspacePickerHeader}>
                <Text style={styles.panelTitle}>Inbox</Text>
                <Pressable
                  accessibilityRole="button"
                  accessibilityLabel="Close"
                  onPress={() => setInboxBrowserOpen(false)}
                >
                  <Text style={styles.workspacePickerClose}>Close</Text>
                </Pressable>
              </View>
              <FlatList
                data={inboxItems}
                keyExtractor={(signal) => recordId(signal)}
                ListEmptyComponent={<Text style={styles.workspacePickerEmpty}>Inbox is clear.</Text>}
                renderItem={({ item: signal }) => {
                  const severity = typeof signal.severity === "string" ? signal.severity : "info";
                  const tone: SummaryTone = severity === "critical" || severity === "error" ? "error" : severity === "warning" ? "warn" : "neutral";
                  return (
                    <Pressable
                      accessibilityRole="button"
                      onPress={() => jumpToSignal(signal)}
                      style={styles.workspacePickerRow}
                    >
                      <View style={styles.browserRowHeader}>
                        <Text numberOfLines={1} style={styles.workspacePickerRowLabel}>
                          {readableWorkspaceId(typeof signal.workspace_id === "string" ? signal.workspace_id : null)}
                        </Text>
                        <View style={[styles.browserPhaseBadge, toneStyle(tone)]}>
                          <Text style={styles.browserPhaseBadgeText}>{severity}</Text>
                        </View>
                      </View>
                      <Text numberOfLines={2} style={styles.browserRowDetail}>
                        {typeof signal.title === "string" && signal.title.trim()
                          ? signal.title
                          : typeof signal.summary === "string"
                            ? signal.summary
                            : "Signal"}
                      </Text>
                    </Pressable>
                  );
                }}
              />
            </SafeAreaView>
          </View>
        </Modal>

        <View style={styles.footer}>
          <Text style={styles.footerText}>
            {updatedAt ? `Last checked ${updatedAt.toLocaleTimeString()}` : "Connecting..."}
          </Text>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: { flex: 1, backgroundColor: "#03090b" },
  page: { flexGrow: 1, paddingBottom: 34, paddingHorizontal: 16, paddingTop: 18 },
  header: { alignItems: "center", flexDirection: "row", gap: 12, justifyContent: "space-between" },
  brandBlock: { flex: 1 },
  eyebrow: { color: "#69f7f0", fontSize: 12, fontWeight: "900", letterSpacing: 1, textTransform: "uppercase" },
  title: { color: "#f6fffb", fontSize: 30, fontWeight: "800", marginTop: 2 },
  badge: {
    alignItems: "center",
    borderColor: "rgba(105, 247, 240, 0.72)",
    borderRadius: 8,
    borderWidth: 1,
    minWidth: 76,
    paddingHorizontal: 10,
    paddingVertical: 8,
  },
  badgeText: { color: "#03100f", fontSize: 10, fontWeight: "900", letterSpacing: 0.8 },
  endpoint: {
    color: "#8fb2b0",
    fontFamily: "monospace",
    fontSize: 11,
    marginTop: 10,
  },
  liveRow: { alignItems: "center", flexDirection: "row", gap: 6, marginTop: 10 },
  liveDot: { borderRadius: 4, height: 8, width: 8 },
  liveDotOn: { backgroundColor: "#3ef7a0" },
  liveDotOff: { backgroundColor: "#f7b23e" },
  liveLabel: { color: "#8fb2b0", fontSize: 10, fontWeight: "800", letterSpacing: 0.6 },
  heroCard: {
    backgroundColor: "#050f12",
    borderColor: "rgba(105, 247, 240, 0.58)",
    borderRadius: 8,
    borderWidth: 1,
    marginTop: 14,
    minHeight: 430,
    overflow: "hidden",
    padding: 16,
    position: "relative",
  },
  holoLineTop: {
    backgroundColor: "rgba(105, 247, 240, 0.26)",
    height: 1,
    left: 18,
    position: "absolute",
    right: 18,
    top: 76,
  },
  holoLineBottom: {
    backgroundColor: "rgba(255, 209, 102, 0.18)",
    bottom: 100,
    height: 1,
    left: 18,
    position: "absolute",
    right: 18,
  },
  heroHeader: { alignItems: "center", flexDirection: "row", justifyContent: "space-between" },
  heroEyebrow: { color: "#9bd9d5", fontSize: 11, fontWeight: "800", letterSpacing: 1, textTransform: "uppercase" },
  heroTime: { color: "#f6fffb", fontSize: 17, fontWeight: "800", marginTop: 4, maxWidth: 210, textTransform: "capitalize" },
  scoreRing: {
    alignItems: "center",
    backgroundColor: "rgba(9, 32, 35, 0.72)",
    borderColor: "rgba(105, 247, 240, 0.72)",
    borderRadius: 32,
    borderWidth: 1,
    height: 64,
    justifyContent: "center",
    width: 64,
  },
  scoreValue: { color: "#f7fffb", fontSize: 21, fontWeight: "900" },
  scoreLabel: { color: "#69f7f0", fontSize: 9, fontWeight: "900", letterSpacing: 1 },
  commandStage: { alignItems: "center", gap: 16, justifyContent: "center", marginTop: 16 },
  vaxonOrb: {
    alignItems: "center",
    height: 188,
    justifyContent: "center",
    position: "relative",
    width: 188,
  },
  orbPingOne: {
    borderColor: "rgba(105, 247, 240, 0.18)",
    borderRadius: 94,
    borderWidth: 1,
    height: 188,
    position: "absolute",
    width: 188,
  },
  orbPingTwo: {
    borderColor: "rgba(255, 209, 102, 0.26)",
    borderRadius: 74,
    borderWidth: 1,
    height: 148,
    position: "absolute",
    width: 148,
  },
  orbAxisVertical: {
    backgroundColor: "rgba(105, 247, 240, 0.2)",
    height: 188,
    position: "absolute",
    width: 1,
  },
  orbAxisHorizontal: {
    backgroundColor: "rgba(105, 247, 240, 0.2)",
    height: 1,
    position: "absolute",
    width: 188,
  },
  vaxonOrbOuter: {
    alignItems: "center",
    backgroundColor: "rgba(4, 18, 22, 0.95)",
    borderColor: "rgba(105, 247, 240, 0.86)",
    borderRadius: 76,
    borderWidth: 1,
    height: 152,
    justifyContent: "center",
    overflow: "hidden",
    width: 152,
  },
  vaxonOrbImage: {
    height: 152,
    opacity: 0.98,
    width: 152,
  },
  orbGlassRing: {
    borderColor: "rgba(234, 255, 252, 0.5)",
    borderRadius: 76,
    borderWidth: 1,
    bottom: 0,
    left: 0,
    position: "absolute",
    right: 0,
    top: 0,
  },
  orbCorePulse: {
    alignItems: "center",
    backgroundColor: "rgba(105, 247, 240, 0.2)",
    borderColor: "rgba(246, 255, 251, 0.82)",
    borderRadius: 23,
    borderWidth: 1,
    height: 46,
    justifyContent: "center",
    position: "absolute",
    width: 46,
  },
  orbCoreText: { color: "#eafffc", fontSize: 13, fontWeight: "900", letterSpacing: 0 },
  orbStateRail: {
    alignItems: "center",
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 7,
    justifyContent: "center",
    marginTop: 2,
  },
  orbStatePill: {
    alignItems: "center",
    backgroundColor: "rgba(8, 21, 25, 0.88)",
    borderColor: "rgba(105, 247, 240, 0.22)",
    borderRadius: 8,
    borderWidth: 1,
    minHeight: 30,
    minWidth: 68,
    justifyContent: "center",
    paddingHorizontal: 9,
    paddingVertical: 7,
  },
  orbStatePillActive: {
    backgroundColor: "rgba(105, 247, 240, 0.18)",
    borderColor: "rgba(105, 247, 240, 0.7)",
  },
  orbStatePillText: { color: "#c9f7f2", fontSize: 10, fontWeight: "900", letterSpacing: 0, textTransform: "uppercase" },
  orbNode: {
    backgroundColor: "#ffd166",
    borderColor: "#fff7d6",
    borderRadius: 5,
    borderWidth: 1,
    height: 10,
    position: "absolute",
    width: 10,
  },
  orbNodeTop: { top: 8 },
  orbNodeRight: { right: 8 },
  orbNodeBottom: { bottom: 8 },
  orbNodeLeft: { left: 8 },
  advisoryPanel: {
    backgroundColor: "rgba(4, 18, 22, 0.92)",
    borderColor: "rgba(105, 247, 240, 0.35)",
    borderRadius: 8,
    borderWidth: 1,
    padding: 14,
    width: "100%",
  },
  advisoryHeader: { alignItems: "center", flexDirection: "row", gap: 8 },
  advisoryLabel: { color: "#a8d9d6", fontSize: 11, fontWeight: "900", letterSpacing: 1, textTransform: "uppercase" },
  heroTitle: { color: "#f6fffb", fontSize: 22, fontWeight: "900", marginTop: 10 },
  heroBody: { color: "#c6d9d7", fontSize: 13, lineHeight: 19, marginTop: 8 },
  heroIntent: { color: "#ffd166", fontSize: 12, fontWeight: "800", lineHeight: 18, marginTop: 10 },
  commandShortcut: {
    alignItems: "center",
    alignSelf: "flex-start",
    backgroundColor: "rgba(105, 247, 240, 0.14)",
    borderColor: "rgba(105, 247, 240, 0.68)",
    borderRadius: 8,
    borderWidth: 1,
    marginTop: 12,
    minHeight: 38,
    justifyContent: "center",
    paddingHorizontal: 14,
    paddingVertical: 9,
  },
  commandShortcutText: { color: "#eafffc", fontSize: 11, fontWeight: "900", letterSpacing: 0.8 },
  telemetryRail: { flexDirection: "row", flexWrap: "wrap", gap: 8, marginTop: 14 },
  telemetryCell: {
    backgroundColor: "rgba(4, 18, 22, 0.76)",
    borderColor: "rgba(105, 247, 240, 0.26)",
    borderRadius: 8,
    borderWidth: 1,
    minHeight: 54,
    paddingHorizontal: 10,
    paddingVertical: 8,
    width: "48.5%",
  },
  telemetryLabel: { color: "#8fb2b0", fontSize: 10, fontWeight: "900", letterSpacing: 0.8, textTransform: "uppercase" },
  telemetryValue: { color: "#f6fffb", fontSize: 13, fontWeight: "800", marginTop: 5 },
  modeRail: {
    backgroundColor: "rgba(7, 18, 21, 0.92)",
    borderColor: "rgba(105, 247, 240, 0.2)",
    borderRadius: 8,
    borderWidth: 1,
    flexDirection: "row",
    marginTop: 12,
    minWidth: "100%",
    paddingHorizontal: 6,
    paddingVertical: 6,
  },
  modePill: {
    alignItems: "center",
    borderColor: "transparent",
    borderRadius: 8,
    borderWidth: 1,
    minHeight: 58,
    minWidth: 92,
    justifyContent: "center",
    paddingHorizontal: 6,
    paddingVertical: 8,
  },
  modePillActive: {
    backgroundColor: "rgba(29, 121, 126, 0.38)",
    borderColor: "rgba(105, 247, 240, 0.74)",
  },
  modeEyebrow: { color: "#698582", fontSize: 9, fontWeight: "900", letterSpacing: 0.7, textTransform: "uppercase" },
  modeEyebrowActive: { color: "#ffd166" },
  modeLabel: { color: "#a9bbb9", fontSize: 12, fontWeight: "900", marginTop: 4 },
  modeLabelActive: { color: "#f6fffb" },
  modeDeck: { marginTop: 14 },
  sectionHeader: { marginBottom: 12 },
  sectionKicker: { color: "#69f7f0", fontSize: 11, fontWeight: "900", letterSpacing: 1, textTransform: "uppercase" },
  sectionTitle: { color: "#f6fffb", fontSize: 22, fontWeight: "900", marginTop: 4 },
  situationSummary: { color: "#d6efed", fontSize: 15, lineHeight: 21, marginBottom: 14, marginTop: 10 },
  statsRow: { flexDirection: "row", flexWrap: "wrap", gap: 9 },
  statCard: {
    backgroundColor: "rgba(9, 24, 28, 0.94)",
    borderColor: "rgba(105, 247, 240, 0.22)",
    borderRadius: 8,
    borderWidth: 1,
    minHeight: 86,
    padding: 12,
    width: "48.5%",
  },
  statCardPressed: { backgroundColor: "rgba(105, 247, 240, 0.1)" },
  statCardHeader: { alignItems: "center", flexDirection: "row", justifyContent: "space-between", marginBottom: 8 },
  statCardChevron: { color: "#5f8482", fontSize: 15, fontWeight: "900" },
  statDot: { borderRadius: 4, height: 8, width: 8 },
  statLabel: { color: "#9bb4b1", fontSize: 11, fontWeight: "900", letterSpacing: 0.7, textTransform: "uppercase" },
  statValue: { color: "#f6fffb", fontSize: 19, fontWeight: "900", marginTop: 8 },
  toneOk: { backgroundColor: "#69f7a9" },
  toneWarn: { backgroundColor: "#ffd166" },
  toneError: { backgroundColor: "#ff7b72" },
  toneNeutral: { backgroundColor: "#8aa1a0" },
  panel: {
    backgroundColor: "rgba(8, 21, 25, 0.95)",
    borderColor: "rgba(105, 247, 240, 0.22)",
    borderRadius: 8,
    borderWidth: 1,
    marginTop: 12,
    minHeight: 110,
    padding: 14,
  },
  panelHeader: { alignItems: "center", flexDirection: "row", gap: 12, justifyContent: "space-between", marginBottom: 14 },
  panelHeaderCopy: { flex: 1 },
  panelTitle: { color: "#f6fffb", fontSize: 20, fontWeight: "900" },
  panelCopy: { color: "#a9bbb9", fontSize: 13, lineHeight: 19, marginTop: 7 },
  panelMeta: { color: "#8fb2b0", fontFamily: "monospace", fontSize: 11, marginTop: 12 },
  chipRow: { gap: 9, paddingBottom: 4, paddingTop: 13 },
  chip: {
    backgroundColor: "rgba(4, 15, 19, 0.86)",
    borderColor: "rgba(105, 247, 240, 0.24)",
    borderRadius: 8,
    borderWidth: 1,
    maxWidth: 210,
    minHeight: 42,
    minWidth: 110,
    paddingHorizontal: 13,
    paddingVertical: 10,
  },
  chipActive: { backgroundColor: "rgba(105, 247, 240, 0.17)", borderColor: "rgba(105, 247, 240, 0.78)" },
  chipText: { color: "#d6efed", fontSize: 13, fontWeight: "800" },
  chipTextActive: { color: "#ffffff" },
  workspaceSearchTrigger: {
    backgroundColor: "rgba(105, 247, 240, 0.12)",
    borderColor: "rgba(105, 247, 240, 0.4)",
    borderRadius: 999,
    borderWidth: 1,
    paddingHorizontal: 12,
    paddingVertical: 6,
  },
  workspaceSearchTriggerText: { color: "#69f7f0", fontSize: 12, fontWeight: "800" },
  workspacePickerBackdrop: { backgroundColor: "rgba(1, 5, 6, 0.72)", flex: 1, justifyContent: "flex-end" },
  workspacePickerBackdropTouch: { flex: 1 },
  workspacePickerSheet: {
    backgroundColor: "#050f12",
    borderColor: "rgba(105, 247, 240, 0.24)",
    borderTopLeftRadius: 16,
    borderTopRightRadius: 16,
    borderWidth: 1,
    maxHeight: "78%",
    paddingHorizontal: 16,
    paddingTop: 16,
  },
  workspacePickerHeader: {
    alignItems: "center",
    flexDirection: "row",
    justifyContent: "space-between",
    marginBottom: 14,
  },
  workspacePickerClose: { color: "#69f7f0", fontSize: 14, fontWeight: "800" },
  workspaceSearchInput: {
    backgroundColor: "rgba(8, 21, 25, 0.95)",
    borderColor: "rgba(105, 247, 240, 0.22)",
    borderRadius: 8,
    borderWidth: 1,
    color: "#f6fffb",
    fontSize: 15,
    marginBottom: 12,
    paddingHorizontal: 12,
    paddingVertical: 10,
  },
  workspacePickerEmpty: { color: "#8fb2b0", fontSize: 13, paddingVertical: 24, textAlign: "center" },
  workspacePickerRow: {
    borderBottomColor: "rgba(105, 247, 240, 0.1)",
    borderBottomWidth: 1,
    paddingVertical: 14,
  },
  workspacePickerRowActive: { backgroundColor: "rgba(105, 247, 240, 0.08)" },
  workspacePickerRowLabel: { color: "#f6fffb", fontSize: 15, fontWeight: "700" },
  workspacePickerRowId: { color: "#8fb2b0", fontFamily: "monospace", fontSize: 11, marginTop: 3 },
  browserSubtitle: { color: "#8fb2b0", fontSize: 12, marginBottom: 10 },
  browserRowHeader: { alignItems: "center", flexDirection: "row", gap: 8, justifyContent: "space-between" },
  browserPhaseBadge: { borderRadius: 999, paddingHorizontal: 8, paddingVertical: 3 },
  browserPhaseBadgeText: { color: "#03090b", fontSize: 10, fontWeight: "900", textTransform: "uppercase" },
  browserRowDetail: { color: "#b7cbca", fontSize: 12, lineHeight: 17, marginTop: 4 },
  focusRow: { gap: 10, marginTop: 12 },
  focusPanel: {
    backgroundColor: "rgba(8, 21, 25, 0.95)",
    borderColor: "rgba(105, 247, 240, 0.22)",
    borderRadius: 8,
    borderWidth: 1,
    padding: 14,
  },
  focusLabel: { color: "#ffd166", fontSize: 11, fontWeight: "900", letterSpacing: 0.8, textTransform: "uppercase" },
  focusTitle: { color: "#f6fffb", fontSize: 17, fontWeight: "900", marginTop: 8 },
  focusBody: { color: "#b7cbca", fontSize: 13, lineHeight: 19, marginTop: 8 },
  input: {
    backgroundColor: "rgba(3, 10, 13, 0.82)",
    borderColor: "rgba(105, 247, 240, 0.24)",
    borderRadius: 8,
    borderWidth: 1,
    color: "#f6fffb",
    fontSize: 14,
    marginTop: 12,
    paddingHorizontal: 12,
    paddingVertical: 12,
  },
  inputMultiline: { minHeight: 92, textAlignVertical: "top" },
  passwordField: {
    alignItems: "center",
    backgroundColor: "rgba(3, 10, 13, 0.82)",
    borderColor: "rgba(105, 247, 240, 0.24)",
    borderRadius: 8,
    borderWidth: 1,
    flexDirection: "row",
    gap: 8,
    marginTop: 12,
    minHeight: 50,
    paddingLeft: 12,
    paddingRight: 6,
  },
  passwordFieldInput: {
    color: "#f6fffb",
    flex: 1,
    fontSize: 14,
    minHeight: 48,
    paddingVertical: 12,
  },
  passwordVisibilityButton: {
    alignItems: "center",
    backgroundColor: "rgba(105, 247, 240, 0.1)",
    borderColor: "rgba(105, 247, 240, 0.42)",
    borderRadius: 8,
    borderWidth: 1,
    minHeight: 36,
    minWidth: 62,
    justifyContent: "center",
    paddingHorizontal: 9,
  },
  passwordVisibilityText: { color: "#eafffc", fontSize: 10, fontWeight: "900", letterSpacing: 0.8 },
  composerInput: {
    fontFamily: "monospace",
    lineHeight: 20,
    maxHeight: 180,
    minHeight: 112,
    textAlignVertical: "top",
  },
  voicePanel: {
    alignItems: "center",
    backgroundColor: "rgba(3, 14, 18, 0.92)",
    borderColor: "rgba(105, 247, 240, 0.34)",
    borderRadius: 8,
    borderWidth: 1,
    flexDirection: "row",
    gap: 12,
    marginTop: 12,
    minHeight: 92,
    padding: 12,
  },
  voiceCopy: { flex: 1, minWidth: 0 },
  voiceLabel: { color: "#69f7f0", fontSize: 11, fontWeight: "900", letterSpacing: 0.9, textTransform: "uppercase" },
  voiceBody: { color: "#c6d9d7", fontSize: 13, lineHeight: 18, marginTop: 6 },
  voiceTranscript: {
    color: "#ffd166",
    fontFamily: "monospace",
    fontSize: 12,
    lineHeight: 17,
    marginTop: 8,
  },
  micButton: {
    alignItems: "center",
    backgroundColor: "rgba(105, 247, 240, 0.12)",
    borderColor: "rgba(105, 247, 240, 0.72)",
    borderRadius: 8,
    borderWidth: 1,
    height: 56,
    justifyContent: "center",
    width: 64,
  },
  micButtonLive: {
    backgroundColor: "rgba(255, 123, 114, 0.22)",
    borderColor: "rgba(255, 123, 114, 0.82)",
  },
  micButtonUnavailable: { opacity: 0.55 },
  micButtonText: { color: "#eafffc", fontSize: 12, fontWeight: "900", letterSpacing: 0 },
  quickCommandRow: {
    gap: 8,
    marginTop: 12,
  },
  quickCommand: {
    backgroundColor: "rgba(255, 209, 102, 0.08)",
    borderColor: "rgba(255, 209, 102, 0.38)",
    borderRadius: 8,
    borderWidth: 1,
    justifyContent: "center",
    minHeight: 44,
    paddingHorizontal: 11,
    paddingVertical: 9,
  },
  quickCommandText: {
    color: "#ffe7a3",
    fontSize: 12,
    fontWeight: "800",
    lineHeight: 17,
  },
  actionButton: {
    alignItems: "center",
    backgroundColor: "#1db8a8",
    borderRadius: 8,
    marginTop: 14,
    minHeight: 48,
    justifyContent: "center",
    paddingHorizontal: 14,
    paddingVertical: 12,
  },
  actionButtonSecondary: {
    alignItems: "center",
    backgroundColor: "rgba(29, 121, 126, 0.28)",
    borderColor: "rgba(105, 247, 240, 0.38)",
    borderRadius: 8,
    borderWidth: 1,
    flexGrow: 1,
    minHeight: 46,
    minWidth: "47%",
    justifyContent: "center",
    paddingHorizontal: 12,
    paddingVertical: 12,
  },
  actionButtonDisabled: { opacity: 0.42 },
  actionButtonText: { color: "#f6fffb", fontSize: 13, fontWeight: "900", letterSpacing: 0.4 },
  actionRow: { flexDirection: "row", flexWrap: "wrap", gap: 9, marginTop: 10 },
  accessBadge: {
    alignItems: "center",
    borderRadius: 8,
    borderWidth: 1,
    minHeight: 30,
    justifyContent: "center",
    paddingHorizontal: 9,
    paddingVertical: 6,
  },
  accessBadgeReady: {
    backgroundColor: "rgba(105, 247, 169, 0.16)",
    borderColor: "rgba(105, 247, 169, 0.62)",
  },
  accessBadgeLocked: {
    backgroundColor: "rgba(255, 209, 102, 0.1)",
    borderColor: "rgba(255, 209, 102, 0.5)",
  },
  accessBadgeText: { color: "#eafffc", fontSize: 10, fontWeight: "900", letterSpacing: 0.7 },
  accessClearButton: {
    alignSelf: "flex-start",
    flexGrow: 0,
    marginTop: 12,
    minWidth: 138,
  },
  statusMessage: { fontSize: 13, lineHeight: 19, marginTop: 12 },
  statusSuccess: { color: "#91f5bb" },
  statusError: { color: "#ffaaa2" },
  statusWorking: { color: "#e3fffb" },
  commandHistoryList: { gap: 10, marginTop: 2 },
  commandHistoryItem: {
    backgroundColor: "rgba(3, 14, 18, 0.9)",
    borderColor: "rgba(105, 247, 240, 0.2)",
    borderRadius: 8,
    borderWidth: 1,
    padding: 12,
  },
  commandHistoryHeader: {
    alignItems: "center",
    flexDirection: "row",
    gap: 8,
    justifyContent: "space-between",
  },
  commandHistorySource: { color: "#eafffc", flex: 1, fontSize: 12, fontWeight: "900" },
  commandHistoryStatus: {
    borderRadius: 8,
    borderWidth: 1,
    fontSize: 9,
    fontWeight: "900",
    overflow: "hidden",
    paddingHorizontal: 7,
    paddingVertical: 4,
  },
  commandHistorySent: {
    borderColor: "rgba(105, 247, 169, 0.66)",
    color: "#91f5bb",
  },
  commandHistoryFailed: {
    borderColor: "rgba(255, 123, 114, 0.7)",
    color: "#ffaaa2",
  },
  commandHistoryQueued: {
    borderColor: "rgba(255, 209, 102, 0.58)",
    color: "#ffe7a3",
  },
  commandHistoryText: { color: "#f6fffb", fontSize: 13, lineHeight: 18, marginTop: 9 },
  commandHistoryResponse: { color: "#9bb4b1", fontSize: 12, lineHeight: 17, marginTop: 7 },
  commandHistoryTime: { color: "#6f8886", fontFamily: "monospace", fontSize: 10, marginTop: 8 },
  list: { gap: 10 },
  listItem: {
    alignItems: "center",
    backgroundColor: "rgba(8, 21, 25, 0.95)",
    borderColor: "rgba(105, 247, 240, 0.22)",
    borderRadius: 8,
    borderWidth: 1,
    flexDirection: "row",
    gap: 12,
    minHeight: 78,
    padding: 12,
  },
  employeeAvatar: {
    alignItems: "center",
    backgroundColor: "rgba(105, 247, 240, 0.18)",
    borderColor: "rgba(255, 209, 102, 0.72)",
    borderRadius: 24,
    borderWidth: 1,
    height: 48,
    justifyContent: "center",
    width: 48,
  },
  employeeAvatarText: { color: "#f6fffb", fontSize: 19, fontWeight: "900" },
  employeeCopy: { flex: 1 },
  listTitle: { color: "#f6fffb", fontSize: 15, fontWeight: "900" },
  listDetail: { color: "#a9bbb9", fontSize: 12, lineHeight: 18, marginTop: 5 },
  grid: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  tile: {
    backgroundColor: "rgba(8, 21, 25, 0.95)",
    borderColor: "rgba(105, 247, 240, 0.22)",
    borderRadius: 8,
    borderWidth: 1,
    minHeight: 82,
    padding: 12,
    width: "48.5%",
  },
  activeTile: { backgroundColor: "rgba(105, 247, 240, 0.17)", borderColor: "rgba(105, 247, 240, 0.76)" },
  dot: { borderRadius: 4, height: 8, marginBottom: 10, width: 8 },
  okDot: { backgroundColor: "#69f7a9" },
  errorDot: { backgroundColor: "#ff7b72" },
  tileLabel: { color: "#e9fffb", fontSize: 14, fontWeight: "900" },
  activeTileLabel: { color: "#ffffff" },
  tileValue: { color: "#8fb2b0", fontSize: 12, marginTop: 4 },
  path: { color: "#8fb2b0", fontFamily: "monospace", fontSize: 11, marginTop: 4 },
  payloadScroller: { flexGrow: 0 },
  payload: { color: "#d6e4e2", fontFamily: "monospace", fontSize: 12, lineHeight: 19 },
  errorPanel: {
    backgroundColor: "rgba(54, 20, 24, 0.88)",
    borderColor: "rgba(255, 123, 114, 0.58)",
    borderRadius: 8,
    borderWidth: 1,
    padding: 14,
  },
  errorTitle: { color: "#ffaaa2", fontSize: 16, fontWeight: "900" },
  errorText: { color: "#ffd5d0", fontFamily: "monospace", fontSize: 12, marginTop: 7 },
  errorHint: { color: "#d8aaa5", fontSize: 13, lineHeight: 19, marginTop: 14 },
  footer: { alignItems: "center", marginTop: 16 },
  footerText: { color: "#8fb2b0", fontSize: 12, lineHeight: 17 },
});

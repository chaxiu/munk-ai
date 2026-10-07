import * as fs from 'node:fs';
import * as os from 'node:os';
import * as path from 'node:path';

import { IOSDeviceBridgeError } from './errors.js';

export interface DiagnosticsContext {
  operation_id?: string | null;
  run_dir?: string | null;
  attempt_index?: number | null;
  app_id?: string | null;
  plan_id?: string | null;
  case_id?: string | null;
}

export interface SessionDiagnosticsSeed {
  sessionId: string;
  deviceUdid: string;
  bundleId: string;
  wdaBundleId: string;
  platformVersion: string | null;
  backendKind: string;
  context?: DiagnosticsContext | null;
}

export interface BridgeDiagnosticsSnapshot {
  session: Record<string, unknown>;
  summary: Record<string, unknown>;
  events_path: string;
  summary_path: string;
  session_path: string;
  tail: Record<string, unknown>[];
}

type Level = 'debug' | 'info' | 'warn' | 'error';

interface SessionDiagnosticsState {
  seed: SessionDiagnosticsSeed;
  rootDir: string;
  sessionPath: string;
  eventsPath: string;
  summaryPath: string;
  createdAt: string;
  lastPhase: string | null;
  lastError: Record<string, unknown> | null;
  eventCount: number;
  summary: Record<string, unknown>;
}

const SENSITIVE_KEY_PATTERN =
  /password|passwd|secret|token|api[_-]?key|authorization|cookie|sudo/i;
const MAX_STRING_LENGTH = 2000;
const MAX_JSON_LENGTH = 6000;
const sessions = new Map<string, SessionDiagnosticsState>();

export function createSessionDiagnostics(seed: SessionDiagnosticsSeed): void {
  const rootDir = resolveDiagnosticsRoot(seed.sessionId, seed.context);
  fs.mkdirSync(rootDir, {recursive: true});
  const state: SessionDiagnosticsState = {
    seed,
    rootDir,
    sessionPath: path.join(rootDir, 'session.json'),
    eventsPath: path.join(rootDir, 'events.jsonl'),
    summaryPath: path.join(rootDir, 'summary.json'),
    createdAt: new Date().toISOString(),
    lastPhase: null,
    lastError: null,
    eventCount: 0,
    summary: {
      session_id: seed.sessionId,
      device_udid: seed.deviceUdid,
      bundle_id: seed.bundleId,
      wda_bundle_id: seed.wdaBundleId,
      platform_version: seed.platformVersion,
      backend_kind: seed.backendKind,
      created_at: new Date().toISOString(),
      diagnostics_root: rootDir,
      context: sanitize(seed.context ?? {}),
      wda_session_created: false,
      app_launch_attempted: false,
    },
  };
  sessions.set(seed.sessionId, state);
  writeJson(state.sessionPath, {
    session_id: seed.sessionId,
    device_udid: seed.deviceUdid,
    bundle_id: seed.bundleId,
    wda_bundle_id: seed.wdaBundleId,
    platform_version: seed.platformVersion,
    backend_kind: seed.backendKind,
    diagnostics_root: rootDir,
    context: sanitize(seed.context ?? {}),
  });
  writeSummary(state);
  logBridgeEvent(seed.sessionId, 'bridge.session.create.success', {
    level: 'info',
    phase: 'session.create',
    details: {
      device_udid: seed.deviceUdid,
      bundle_id: seed.bundleId,
      wda_bundle_id: seed.wdaBundleId,
      platform_version: seed.platformVersion,
      backend_kind: seed.backendKind,
    },
  });
}

export function hasSessionDiagnostics(sessionId: string): boolean {
  return sessions.has(sessionId);
}

export function updateSessionDiagnostics(
  sessionId: string,
  values: Record<string, unknown>,
): void {
  const state = sessions.get(sessionId);
  if (!state) {
    return;
  }
  const sanitizedValues = sanitize(values) as Record<string, unknown>;
  state.summary = {
    ...state.summary,
    ...sanitizedValues,
  };
  writeSummary(state);
}

export function logBridgeEvent(
  sessionId: string | null | undefined,
  event: string,
  options: {
    level?: Level;
    phase?: string;
    ok?: boolean;
    duration_ms?: number;
    details?: unknown;
    error?: unknown;
  } = {},
): void {
  const ts = new Date().toISOString();
  const state = sessionId ? sessions.get(sessionId) : undefined;
  const level = options.level ?? (options.error ? 'error' : 'info');
  const phase = options.phase ?? event;
  const payload: Record<string, unknown> = {
    ts,
    level,
    event,
    session_id: sessionId ?? null,
    operation_id: state?.seed.context?.operation_id ?? null,
    run_dir: state?.seed.context?.run_dir ?? null,
    attempt_index: state?.seed.context?.attempt_index ?? null,
    app_id: state?.seed.context?.app_id ?? null,
    plan_id: state?.seed.context?.plan_id ?? null,
    case_id: state?.seed.context?.case_id ?? null,
    device_udid: state?.seed.deviceUdid ?? null,
    backend_kind: state?.seed.backendKind ?? null,
    phase,
    ok: options.ok ?? !options.error,
  };
  if (typeof options.duration_ms === 'number') {
    payload.duration_ms = Math.round(options.duration_ms);
  }
  if (options.details !== undefined) {
    payload.details = sanitize(options.details);
  }
  if (options.error !== undefined) {
    payload.error = normalizeError(options.error);
  }
  if (state) {
    state.eventCount += 1;
    state.lastPhase = phase;
    if (options.error !== undefined) {
      state.lastError = normalizeError(options.error);
    }
    appendJsonLine(state.eventsPath, payload);
    writeSummary(state);
    return;
  }
  console.error(JSON.stringify(payload));
}

export async function withBridgeSpan<T>(
  sessionId: string,
  eventBase: string,
  phase: string,
  details: Record<string, unknown> | undefined,
  fn: () => Promise<T>,
): Promise<T> {
  const start = Date.now();
  logBridgeEvent(sessionId, `${eventBase}.start`, {
    level: 'info',
    phase,
    details,
  });
  try {
    const result = await fn();
    logBridgeEvent(sessionId, `${eventBase}.success`, {
      level: 'info',
      phase,
      ok: true,
      duration_ms: Date.now() - start,
    });
    return result;
  } catch (error) {
    logBridgeEvent(sessionId, `${eventBase}.failure`, {
      level: 'error',
      phase,
      ok: false,
      duration_ms: Date.now() - start,
      error,
    });
    throw error;
  }
}

export function getSessionDiagnostics(
  sessionId: string,
): BridgeDiagnosticsSnapshot {
  const state = sessions.get(sessionId);
  if (!state) {
    throw new IOSDeviceBridgeError(
      'session_not_found',
      `bridge session diagnostics not found: ${sessionId}`,
      404,
    );
  }
  return {
    session: readJsonObject(state.sessionPath),
    summary: buildSummary(state),
    events_path: state.eventsPath,
    summary_path: state.summaryPath,
    session_path: state.sessionPath,
    tail: readJsonlTail(state.eventsPath, 80),
  };
}

export function closeSessionDiagnostics(sessionId: string): void {
  logBridgeEvent(sessionId, 'bridge.session.close', {
    level: 'info',
    phase: 'session.close',
    ok: true,
  });
  sessions.delete(sessionId);
}

export function normalizeForDiagnostics(value: unknown): unknown {
  return sanitize(value);
}

export function normalizeError(error: unknown): Record<string, unknown> {
  if (error instanceof IOSDeviceBridgeError) {
    return sanitize({
      name: error.name,
      code: error.code,
      message: error.message,
      status_code: error.statusCode,
      details: error.details ?? null,
      stack: error.stack,
    }) as Record<string, unknown>;
  }
  if (error instanceof Error) {
    return sanitize({
      name: error.name,
      message: error.message,
      stack: error.stack,
    }) as Record<string, unknown>;
  }
  return sanitize({message: String(error)}) as Record<string, unknown>;
}

function resolveDiagnosticsRoot(
  sessionId: string,
  context?: DiagnosticsContext | null,
): string {
  const runDir = typeof context?.run_dir === 'string' && context.run_dir
    ? context.run_dir
    : null;
  if (runDir) {
    return path.join(runDir, 'ios_bridge');
  }
  const base = process.env.MUNK_IOS_BRIDGE_LOG_DIR
    || path.join(os.tmpdir(), 'munk-ios-device-bridge');
  return path.join(base, sessionId);
}

function buildSummary(state: SessionDiagnosticsState): Record<string, unknown> {
  return {
    ...state.summary,
    event_count: state.eventCount,
    last_phase: state.lastPhase,
    last_error: state.lastError,
    events_path: state.eventsPath,
    session_path: state.sessionPath,
    summary_path: state.summaryPath,
    updated_at: new Date().toISOString(),
  };
}

function writeSummary(state: SessionDiagnosticsState): void {
  writeJson(state.summaryPath, buildSummary(state));
}

function sanitize(value: unknown): unknown {
  if (value === null || value === undefined) {
    return value ?? null;
  }
  if (typeof value === 'string') {
    return value.length > MAX_STRING_LENGTH
      ? `${value.slice(0, MAX_STRING_LENGTH)}...`
      : value;
  }
  if (typeof value === 'number' || typeof value === 'boolean') {
    return value;
  }
  if (Array.isArray(value)) {
    return value.map((item) => sanitize(item));
  }
  if (typeof value === 'object') {
    const output: Record<string, unknown> = {};
    for (const [key, item] of Object.entries(value as Record<string, unknown>)) {
      if (SENSITIVE_KEY_PATTERN.test(key)) {
        output[key] = '<redacted>';
        continue;
      }
      output[key] = sanitize(item);
    }
    return compactIfLarge(output);
  }
  return String(value);
}

function compactIfLarge(value: unknown): unknown {
  try {
    const serialized = JSON.stringify(value);
    if (serialized.length <= MAX_JSON_LENGTH) {
      return value;
    }
    return {
      truncated: true,
      preview: serialized.slice(0, MAX_JSON_LENGTH),
    };
  } catch {
    return String(value);
  }
}

function writeJson(filePath: string, payload: unknown): void {
  fs.mkdirSync(path.dirname(filePath), {recursive: true});
  fs.writeFileSync(
    filePath,
    `${JSON.stringify(payload, null, 2)}\n`,
    'utf8',
  );
}

function appendJsonLine(filePath: string, payload: unknown): void {
  fs.mkdirSync(path.dirname(filePath), {recursive: true});
  fs.appendFileSync(filePath, `${JSON.stringify(payload)}\n`, 'utf8');
}

function readJsonObject(filePath: string): Record<string, unknown> {
  try {
    const loaded = JSON.parse(fs.readFileSync(filePath, 'utf8'));
    return loaded && typeof loaded === 'object'
      ? loaded as Record<string, unknown>
      : {};
  } catch {
    return {};
  }
}

function readJsonlTail(filePath: string, maxLines: number): Record<string, unknown>[] {
  try {
    return fs.readFileSync(filePath, 'utf8')
      .trim()
      .split('\n')
      .filter(Boolean)
      .slice(-maxLines)
      .map((line) => JSON.parse(line))
      .filter((item) => item && typeof item === 'object') as Record<string, unknown>[];
  } catch {
    return [];
  }
}

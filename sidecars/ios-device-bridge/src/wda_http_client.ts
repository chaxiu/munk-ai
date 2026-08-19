import axios, {type Method} from 'axios';

import {
  buildAccessibilityTreePayload,
  buildCurrentAppPayload,
  type BridgeAccessibilityTreePayload,
  type BridgeCurrentAppPayload,
} from './device_payloads.js';
import {
  logBridgeEvent,
  normalizeForDiagnostics,
  updateSessionDiagnostics,
} from './diagnostics.js';
import {IOSDeviceBridgeError} from './errors.js';

const WDA_UI_TESTING_AUTHORIZATION_PATTERNS = [
  'xctdaemonerrordomain code=41',
  'not authorized for performing ui testing actions',
];

export class WdaHttpClient {
  private readonly baseUrl: string;
  private readonly bundleId: string;
  private readonly diagnosticsSessionId: string;
  private sessionId: string | null = null;

  constructor(baseUrl: string, bundleId: string, diagnosticsSessionId: string) {
    this.baseUrl = baseUrl.replace(/\/$/, '');
    this.bundleId = bundleId;
    this.diagnosticsSessionId = diagnosticsSessionId;
  }

  async probeStatus(): Promise<boolean> {
    try {
      await this.request('GET', '/status');
      return true;
    } catch {
      return false;
    }
  }

  async ensureReady(): Promise<void> {
    await this.ensureSessionId();
  }

  async screenshotPngBase64(): Promise<string> {
    const payload = await this.request('GET', '/screenshot');
    const value = payload.value;
    if (typeof value !== 'string' || !value) {
      throw new IOSDeviceBridgeError(
        'wda_invalid_response',
        'WDA screenshot response missing base64 payload',
        502,
      );
    }
    return value;
  }

  async tap(x: number, y: number): Promise<void> {
    await this.sessionRequest('POST', '/wda/tap', {x, y});
  }

  async longPress(
    x: number,
    y: number,
    durationSec: number | null,
  ): Promise<void> {
    await this.sessionRequest('POST', '/wda/touchAndHold', {
      x,
      y,
      duration: durationSec ?? 1.0,
    });
  }

  async swipe(payload: {
    startX: number;
    startY: number;
    endX: number;
    endY: number;
    durationSec: number | null;
  }): Promise<void> {
    const body: Record<string, number> = {
      fromX: payload.startX,
      fromY: payload.startY,
      toX: payload.endX,
      toY: payload.endY,
    };
    if (payload.durationSec !== null) {
      body.duration = payload.durationSec;
    }
    await this.sessionRequest('POST', '/wda/dragfromtoforduration', body);
  }

  async typeText(text: string): Promise<void> {
    await this.sessionRequest('POST', '/wda/keys', {value: Array.from(text)});
  }

  async clearText(): Promise<void> {
    const payload = await this.sessionRequest('GET', '/element/active');
    const elementId = parseWdaElementId(payload.value, 'active element');
    await this.clearElement(elementId);
  }

  async findElement(using: string, value: string): Promise<string> {
    const payload = await this.sessionRequest('POST', '/element', {using, value});
    return parseWdaElementId(payload.value, `find using=${using}`);
  }

  async clickElement(elementId: string): Promise<void> {
    await this.sessionRequest('POST', `/element/${elementId}/click`);
  }

  async clearElement(elementId: string): Promise<void> {
    await this.sessionRequest('POST', `/element/${elementId}/clear`);
  }

  async setElementValue(elementId: string, text: string): Promise<void> {
    await this.sessionRequest('POST', `/element/${elementId}/value`, {
      value: Array.from(text),
    });
  }

  async getElementAttribute(
    elementId: string,
    name: string,
  ): Promise<string | null> {
    const payload = await this.sessionRequest(
      'GET',
      `/element/${elementId}/attribute/${name}`,
    );
    return parseWdaAttributeValue(payload.value);
  }

  async press(key: string): Promise<void> {
    const normalized = key.trim().toLowerCase();
    if (normalized === 'home') {
      await this.request('POST', '/wda/homescreen');
      return;
    }
    await this.sessionRequest('POST', '/wda/keys', {value: [key]});
  }

  async dismissSoftKeyboard(): Promise<void> {
    await this.sessionRequest(
      'POST',
      '/wda/keyboard/dismiss',
      {keyNames: []},
      true,
    );
  }

  async currentApp(): Promise<BridgeCurrentAppPayload> {
    const payload = await this.request('GET', '/wda/activeAppInfo');
    return buildCurrentAppPayload(payload.value);
  }

  async windowSize(): Promise<{width: number; height: number}> {
    const payload = await this.request('GET', '/window/size');
    if (!payload.value || typeof payload.value !== 'object') {
      throw new IOSDeviceBridgeError(
        'wda_invalid_response',
        'WDA window size response missing value object',
        502,
      );
    }
    const value = payload.value as Record<string, unknown>;
    return {
      width: Number(value.width ?? 0),
      height: Number(value.height ?? 0),
    };
  }

  async accessibilityTree(): Promise<BridgeAccessibilityTreePayload | null> {
    const payload = await this.request('GET', '/source?format=json');
    return buildAccessibilityTreePayload(payload.value);
  }

  async launchApp(bundleId: string): Promise<void> {
    updateSessionDiagnostics(this.diagnosticsSessionId, {
      app_launch_attempted: true,
      last_app_launch_bundle_id: bundleId,
    });
    await this.sessionRequest('POST', '/wda/apps/launch', {bundleId});
  }

  async terminateApp(bundleId: string): Promise<void> {
    await this.sessionRequest('POST', '/wda/apps/terminate', {bundleId});
  }

  async close(): Promise<void> {
    if (!this.sessionId) {
      return;
    }
    const sessionId = this.sessionId;
    this.sessionId = null;
    try {
      await this.request('DELETE', `/session/${sessionId}`);
    } catch {
      // Best-effort teardown.
    }
  }

  private async sessionRequest(
    method: Method,
    route: string,
    body?: object,
    allowError = false,
  ): Promise<Record<string, unknown>> {
    const sessionId = await this.ensureSessionId();
    return await this.request(
      method,
      `/session/${sessionId}${route}`,
      body,
      allowError,
    );
  }

  private async ensureSessionId(): Promise<string> {
    if (this.sessionId) {
      return this.sessionId;
    }
    const sessionPayload = buildWdaCreateSessionPayload(this.bundleId);
    let responseStatus: number | null = null;
    let payload: Record<string, unknown> = {};
    const start = Date.now();
    logBridgeEvent(this.diagnosticsSessionId, 'bridge.wda.session.create.start', {
      phase: 'wda.session',
      details: {
        baseUrl: this.baseUrl,
        bundleId: this.bundleId,
        requestBody: sessionPayload,
      },
    });
    try {
      const response = await axios.request<Record<string, unknown>>({
        method: 'POST',
        url: `${this.baseUrl}/session`,
        data: sessionPayload,
        timeout: 10000,
        validateStatus: () => true,
      });
      responseStatus = response.status;
      payload = response.data ?? {};
    } catch (error) {
      if (axios.isAxiosError(error)) {
        logBridgeEvent(this.diagnosticsSessionId, 'bridge.wda.session.create.failure', {
          level: 'error',
          phase: 'wda.session',
          ok: false,
          duration_ms: Date.now() - start,
          error,
        });
        throw new IOSDeviceBridgeError(
          'wda_request_failed',
          `WDA request failed for POST /session: ${error.message}`,
          502,
        );
      }
      throw new IOSDeviceBridgeError(
        'wda_request_failed',
        `WDA request failed for POST /session: ${error instanceof Error ? error.message : String(error)}`,
        502,
      );
    }
    const sessionId = extractWdaSessionId(payload);
    if (sessionId) {
      this.sessionId = sessionId;
      updateSessionDiagnostics(this.diagnosticsSessionId, {
        wda_session_created: true,
        wda_session_id: sessionId,
      });
      logBridgeEvent(this.diagnosticsSessionId, 'bridge.wda.session.create.success', {
        phase: 'wda.session',
        ok: true,
        duration_ms: Date.now() - start,
        details: {responseStatus, wdaSessionId: sessionId},
      });
      return sessionId;
    }
    if (isWdaUiTestingAuthorizationPayload(payload)) {
      throw new IOSDeviceBridgeError(
        'wda_ui_testing_not_authorized',
        'WDA started but iOS rejected UI testing actions. Unlock or wake the device and retry.',
        502,
        {needs_device_unlock: true, response_status: responseStatus, response_payload: payload},
      );
    }
    if (responseStatus !== null && responseStatus >= 400) {
      const payloadMessage = lookup(payload, 'value.message', 'message');
      throw new IOSDeviceBridgeError(
        'wda_request_failed',
        payloadMessage
          ? `WDA request failed for POST /session: ${payloadMessage}`
          : `WDA request failed for POST /session: HTTP ${responseStatus}`,
        502,
      );
    }
    throw new IOSDeviceBridgeError(
      'wda_invalid_response',
      'WDA create session response missing sessionId',
      502,
      {response_payload: payload},
    );
  }

  private async request(
    method: Method,
    path: string,
    body?: object,
    allowError = false,
  ): Promise<Record<string, unknown>> {
    const start = Date.now();
    logBridgeEvent(this.diagnosticsSessionId, 'bridge.wda.http.request', {
      level: 'debug',
      phase: `wda.http ${method} ${path}`,
      details: {method, path, baseUrl: this.baseUrl, requestBody: body ?? null},
    });
    try {
      const response = await axios.request<Record<string, unknown>>({
        method,
        url: `${this.baseUrl}${path}`,
        data: body,
        timeout: 10000,
        validateStatus: allowError ? () => true : undefined,
      });
      logBridgeEvent(this.diagnosticsSessionId, 'bridge.wda.http.response', {
        level: 'debug',
        phase: `wda.http ${method} ${path}`,
        ok: true,
        duration_ms: Date.now() - start,
        details: {method, path, status: response.status},
      });
      if (allowError && response.status >= 400) {
        return {};
      }
      return response.data ?? {};
    } catch (error) {
      logBridgeEvent(this.diagnosticsSessionId, 'bridge.wda.http.error', {
        level: 'error',
        phase: `wda.http ${method} ${path}`,
        ok: false,
        duration_ms: Date.now() - start,
        error,
      });
      throw new IOSDeviceBridgeError(
        'wda_request_failed',
        `WDA request failed for ${method} ${path}: ${error instanceof Error ? error.message : String(error)}`,
        502,
      );
    }
  }
}

export function buildWdaCreateSessionPayload(
  bundleId: string,
): Record<string, unknown> {
  return {
    capabilities: {
      firstMatch: [
        {
          bundleId,
          arguments: [],
          environment: {},
          eventloopIdleDelaySec: 0,
          shouldWaitForQuiescence: true,
          maxTypingFrequency: 60,
          shouldUseSingletonTestManager: true,
          shouldTerminateApp: true,
          forceAppLaunch: true,
          useNativeCachingStrategy: true,
        },
      ],
      alwaysMatch: {},
    },
  };
}

function extractWdaSessionId(payload: Record<string, unknown>): string | null {
  const direct = typeof payload.sessionId === 'string' ? payload.sessionId : null;
  const nested =
    payload.value &&
    typeof payload.value === 'object' &&
    typeof (payload.value as Record<string, unknown>).sessionId === 'string'
      ? ((payload.value as Record<string, unknown>).sessionId as string)
      : null;
  return direct ?? nested;
}

function parseWdaElementId(value: unknown, context: string): string {
  if (!value || typeof value !== 'object') {
    throw new IOSDeviceBridgeError(
      'wda_invalid_response',
      `WDA ${context} response missing value object`,
      502,
    );
  }
  const mapping = value as Record<string, unknown>;
  const elementId =
    (typeof mapping['element-6066-11e4-a52e-4f735466cecf'] === 'string'
      ? mapping['element-6066-11e4-a52e-4f735466cecf']
      : null) ??
    (typeof mapping.ELEMENT === 'string' ? mapping.ELEMENT : null);
  if (!elementId) {
    throw new IOSDeviceBridgeError(
      'wda_invalid_response',
      `WDA ${context} response missing element identifier`,
      502,
    );
  }
  return elementId;
}

function parseWdaAttributeValue(value: unknown): string | null {
  if (value === null || value === undefined) {
    return null;
  }
  if (typeof value === 'boolean') {
    return value ? 'true' : 'false';
  }
  if (typeof value === 'number') {
    return String(value);
  }
  if (typeof value === 'string') {
    return value;
  }
  return null;
}

function isWdaUiTestingAuthorizationPayload(
  payload: Record<string, unknown> | null | undefined,
): boolean {
  if (!payload) {
    return false;
  }
  const serialized = JSON.stringify(normalizeForDiagnostics(payload)).toLowerCase();
  return WDA_UI_TESTING_AUTHORIZATION_PATTERNS.every((pattern) =>
    serialized.includes(pattern),
  );
}

function lookup(
  mapping: Record<string, unknown>,
  ...paths: string[]
): string | null {
  for (const path of paths) {
    let current: unknown = mapping;
    for (const segment of path.split('.')) {
      if (!current || typeof current !== 'object' || Array.isArray(current)) {
        current = undefined;
        break;
      }
      current = (current as Record<string, unknown>)[segment];
    }
    if (typeof current === 'string' && current) {
      return current;
    }
  }
  return null;
}

export {isWdaUiTestingAuthorizationPayload};

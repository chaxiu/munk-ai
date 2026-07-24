import {randomUUID} from 'node:crypto';

import {
  createSessionDiagnostics,
  closeSessionDiagnostics,
  getSessionDiagnostics,
  hasSessionDiagnostics,
  logBridgeEvent,
  updateSessionDiagnostics,
  withBridgeSpan,
  type BridgeDiagnosticsSnapshot,
} from './diagnostics.js';
import type {
  BridgeAccessibilityTreePayload,
  BridgeCurrentAppPayload,
} from './device_payloads.js';
import {IOSDeviceBridgeError} from './errors.js';
import type {
  CreateSessionRequest,
  DeviceBackendKind,
  DeviceInfo,
  SessionInfo,
} from './session_types.js';
import {DEFAULT_WDA_PORT, WdaConnectionManager, type WdaConnectionInfo} from './wda_connection.js';
import {buildWdaCreateSessionPayload, WdaHttpClient} from './wda_http_client.js';
import {
  createDefaultWdaLauncher,
  type WdaLauncher,
} from './wda_launcher.js';
import {
  listRealDevices,
  selectBackendKind,
} from './device_discovery.js';

export type {CreateSessionRequest, DeviceBackendKind, DeviceInfo, SessionInfo};
export {buildWdaCreateSessionPayload};
export {AppiumPreinstalledWdaLauncher} from './wda_launcher.js';
export {WdaConnectionManager} from './wda_connection.js';
export {listRealDevices, selectBackendKind};

const DEFAULT_WDA_BUNDLE_ID = 'sh.munk.wda.xctrunner';

class DeviceSession {
  private readonly info: SessionInfo;
  private readonly connectionManager: WdaConnectionManager;
  private readonly launcher: WdaLauncher;
  private client: WdaHttpClient | null = null;
  private connection: WdaConnectionInfo | null = null;
  private connectionReady = false;
  private closed = false;

  constructor(
    info: SessionInfo,
    connectionManager: WdaConnectionManager,
    launcher: WdaLauncher | null = null,
  ) {
    this.info = info;
    this.connectionManager = connectionManager;
    this.launcher = launcher ?? createDefaultWdaLauncher(info);
  }

  sessionInfo(): SessionInfo {
    return this.info;
  }

  async ensureWdaReady(): Promise<void> {
    await withBridgeSpan(
      this.info.sessionId,
      'bridge.wda.ensure-ready',
      'wda.ensure-ready',
      {
        platform_version: this.info.platformVersion,
        backend_kind: this.info.backendKind,
        wda_port: DEFAULT_WDA_PORT,
      },
      async () => {
        const client = await this.ensureClient();
        if (!this.connection) {
          throw new IOSDeviceBridgeError(
            'wda_connection_failed',
            'WDA connection was not established',
            502,
          );
        }
        await this.launcher.launchAndWaitReady(client, this.connection);
      },
    );
  }

  async screenshotPngBase64(): Promise<string> {
    return await (await this.ensureClient()).screenshotPngBase64();
  }

  async tap(x: number, y: number): Promise<void> {
    await (await this.ensureClient()).tap(x, y);
  }

  async longPress(
    x: number,
    y: number,
    durationSec: number | null,
  ): Promise<void> {
    await (await this.ensureClient()).longPress(x, y, durationSec);
  }

  async swipe(payload: {
    startX: number;
    startY: number;
    endX: number;
    endY: number;
    durationSec: number | null;
  }): Promise<void> {
    await (await this.ensureClient()).swipe(payload);
  }

  async typeText(text: string): Promise<void> {
    await (await this.ensureClient()).typeText(text);
  }

  async clearText(): Promise<void> {
    await (await this.ensureClient()).clearText();
  }

  async press(key: string): Promise<void> {
    await (await this.ensureClient()).press(key);
  }

  async dismissSoftKeyboard(): Promise<void> {
    await (await this.ensureClient()).dismissSoftKeyboard();
  }

  async currentApp(): Promise<BridgeCurrentAppPayload> {
    return await (await this.ensureClient()).currentApp();
  }

  async windowSize(): Promise<{width: number; height: number}> {
    return await (await this.ensureClient()).windowSize();
  }

  async accessibilityTree(): Promise<BridgeAccessibilityTreePayload | null> {
    return await (await this.ensureClient()).accessibilityTree();
  }

  async launchApp(bundleId: string): Promise<void> {
    await withBridgeSpan(
      this.info.sessionId,
      'bridge.app.launch',
      'app.launch',
      {bundle_id: bundleId},
      async () => {
        await (await this.ensureClient()).launchApp(bundleId);
      },
    );
  }

  async terminateApp(bundleId: string): Promise<void> {
    await withBridgeSpan(
      this.info.sessionId,
      'bridge.app.terminate',
      'app.terminate',
      {bundle_id: bundleId},
      async () => {
        await (await this.ensureClient()).terminateApp(bundleId);
      },
    );
  }

  async close(): Promise<void> {
    if (this.closed) {
      return;
    }
    this.closed = true;
    try {
      logBridgeEvent(this.info.sessionId, 'bridge.session.close.start', {
        phase: 'session.close',
      });
      await this.launcher.close();
      await this.client?.close();
      this.client = null;
      if (this.connectionReady && this.connection) {
        await this.connectionManager.releaseConnection(
          this.info.sessionId,
          this.info.deviceUdid,
          this.connection.localPort,
        );
        this.connectionReady = false;
        this.connection = null;
      }
    } finally {
      logBridgeEvent(this.info.sessionId, 'bridge.session.close.success', {
        phase: 'session.close',
      });
    }
  }

  private async ensureClient(): Promise<WdaHttpClient> {
    if (this.client) {
      return this.client;
    }
    if (!this.connectionReady) {
      this.connection = await this.connectionManager.requestConnection(
        this.info.sessionId,
        this.info.deviceUdid,
        this.info.platformVersion,
      );
      this.connectionReady = true;
      updateSessionDiagnostics(this.info.sessionId, {
        forwarded_port: this.connection.localPort,
        remote_wda_port: this.connection.remotePort,
      });
    }
    this.client = new WdaHttpClient(
      this.connection!.baseUrl,
      this.info.bundleId,
      this.info.sessionId,
    );
    return this.client;
  }
}

export class IOSDeviceBridgeSessionManager {
  private readonly sessions = new Map<string, DeviceSession>();
  private readonly connectionManager: WdaConnectionManager;

  constructor(options?: {connectionManager?: WdaConnectionManager}) {
    this.connectionManager =
      options?.connectionManager ?? new WdaConnectionManager();
  }

  async createSession(request: CreateSessionRequest): Promise<SessionInfo> {
    if (!request.device_udid) {
      throw new IOSDeviceBridgeError(
        'invalid_request',
        'device_udid is required',
        400,
      );
    }
    if (!request.bundle_id) {
      throw new IOSDeviceBridgeError(
        'invalid_request',
        'bundle_id is required',
        400,
      );
    }
    const info: SessionInfo = {
      sessionId: randomUUID(),
      deviceUdid: request.device_udid,
      bundleId: request.bundle_id,
      wdaBundleId: request.wda_bundle_id ?? DEFAULT_WDA_BUNDLE_ID,
      platformVersion: request.platform_version ?? null,
      backendKind: selectBackendKind(request.platform_version ?? null),
    };
    createSessionDiagnostics({
      sessionId: info.sessionId,
      deviceUdid: info.deviceUdid,
      bundleId: info.bundleId,
      wdaBundleId: info.wdaBundleId,
      platformVersion: info.platformVersion,
      backendKind: info.backendKind,
      context: request.diagnostics ?? null,
    });
    try {
      const backend = new DeviceSession(info, this.connectionManager);
      this.sessions.set(info.sessionId, backend);
      return info;
    } catch (error) {
      logBridgeEvent(info.sessionId, 'bridge.session.create.failure', {
        level: 'error',
        phase: 'session.create',
        ok: false,
        error,
      });
      throw error;
    }
  }

  getSessionInfo(sessionId: string): SessionInfo {
    return this.getSession(sessionId).sessionInfo();
  }

  async deleteSession(sessionId: string): Promise<void> {
    const session = this.sessions.get(sessionId);
    if (!session) {
      if (hasSessionDiagnostics(sessionId)) {
        closeSessionDiagnostics(sessionId);
      }
      return;
    }
    this.sessions.delete(sessionId);
    try {
      await session.close();
    } finally {
      closeSessionDiagnostics(sessionId);
    }
  }

  async closeAll(): Promise<void> {
    for (const sessionId of [...this.sessions.keys()]) {
      await this.deleteSession(sessionId);
    }
  }

  async ensureWdaReady(sessionId: string): Promise<SessionInfo> {
    const session = this.getSession(sessionId);
    await session.ensureWdaReady();
    return session.sessionInfo();
  }

  getSessionDiagnostics(sessionId: string): BridgeDiagnosticsSnapshot {
    this.getSession(sessionId);
    return getSessionDiagnostics(sessionId);
  }

  async screenshotPngBase64(sessionId: string): Promise<string> {
    return await this.getSession(sessionId).screenshotPngBase64();
  }

  async tap(sessionId: string, x: number, y: number): Promise<void> {
    await this.getSession(sessionId).tap(x, y);
  }

  async longPress(
    sessionId: string,
    x: number,
    y: number,
    durationSec: number | null,
  ): Promise<void> {
    await this.getSession(sessionId).longPress(x, y, durationSec);
  }

  async swipe(
    sessionId: string,
    payload: {
      startX: number;
      startY: number;
      endX: number;
      endY: number;
      durationSec: number | null;
    },
  ): Promise<void> {
    await this.getSession(sessionId).swipe(payload);
  }

  async typeText(sessionId: string, text: string): Promise<void> {
    await this.getSession(sessionId).typeText(text);
  }

  async clearText(sessionId: string): Promise<void> {
    await this.getSession(sessionId).clearText();
  }

  async press(sessionId: string, key: string): Promise<void> {
    await this.getSession(sessionId).press(key);
  }

  async dismissSoftKeyboard(sessionId: string): Promise<void> {
    await this.getSession(sessionId).dismissSoftKeyboard();
  }

  async currentApp(sessionId: string): Promise<BridgeCurrentAppPayload> {
    return await this.getSession(sessionId).currentApp();
  }

  async windowSize(
    sessionId: string,
  ): Promise<{width: number; height: number}> {
    return await this.getSession(sessionId).windowSize();
  }

  async accessibilityTree(
    sessionId: string,
  ): Promise<BridgeAccessibilityTreePayload | null> {
    return await this.getSession(sessionId).accessibilityTree();
  }

  async launchApp(sessionId: string, bundleId: string): Promise<void> {
    await this.getSession(sessionId).launchApp(bundleId);
  }

  async terminateApp(sessionId: string, bundleId: string): Promise<void> {
    await this.getSession(sessionId).terminateApp(bundleId);
  }

  private getSession(sessionId: string): DeviceSession {
    const session = this.sessions.get(sessionId);
    if (!session) {
      throw new IOSDeviceBridgeError(
        'session_not_found',
        `bridge session not found: ${sessionId}`,
        404,
      );
    }
    return session;
  }
}

export class WdaBackend extends DeviceSession {
  constructor(
    _kind: DeviceBackendKind,
    info: SessionInfo,
    _unusedConnectorFactory?: unknown,
    _onClose?: unknown,
    launcher?: WdaLauncher | null,
    connectionManager?: WdaConnectionManager,
  ) {
    super(
      info,
      connectionManager ?? new WdaConnectionManager(),
      launcher ?? createDefaultWdaLauncher(info),
    );
  }
}

import { randomUUID } from 'node:crypto';
import { createSessionDiagnostics, closeSessionDiagnostics, getSessionDiagnostics, hasSessionDiagnostics, logBridgeEvent, updateSessionDiagnostics, withBridgeSpan, } from './diagnostics.js';
import { IOSDeviceBridgeError } from './errors.js';
import { DEFAULT_WDA_PORT, WdaConnectionManager } from './wda_connection.js';
import { buildWdaCreateSessionPayload, WdaHttpClient } from './wda_http_client.js';
import { createDefaultWdaLauncher, } from './wda_launcher.js';
import { listRealDevices, selectBackendKind, } from './device_discovery.js';
export { buildWdaCreateSessionPayload };
export { AppiumPreinstalledWdaLauncher } from './wda_launcher.js';
export { WdaConnectionManager } from './wda_connection.js';
export { listRealDevices, selectBackendKind };
const DEFAULT_WDA_BUNDLE_ID = 'sh.munk.wda.xctrunner';
class DeviceSession {
    info;
    connectionManager;
    launcher;
    client = null;
    connection = null;
    connectionReady = false;
    closed = false;
    constructor(info, connectionManager, launcher = null) {
        this.info = info;
        this.connectionManager = connectionManager;
        this.launcher = launcher ?? createDefaultWdaLauncher(info);
    }
    sessionInfo() {
        return this.info;
    }
    async ensureWdaReady() {
        await withBridgeSpan(this.info.sessionId, 'bridge.wda.ensure-ready', 'wda.ensure-ready', {
            platform_version: this.info.platformVersion,
            backend_kind: this.info.backendKind,
            wda_port: DEFAULT_WDA_PORT,
        }, async () => {
            const client = await this.ensureClient();
            if (!this.connection) {
                throw new IOSDeviceBridgeError('wda_connection_failed', 'WDA connection was not established', 502);
            }
            await this.launcher.launchAndWaitReady(client, this.connection);
        });
    }
    async screenshotPngBase64() {
        return await (await this.ensureClient()).screenshotPngBase64();
    }
    async tap(x, y) {
        await (await this.ensureClient()).tap(x, y);
    }
    async longPress(x, y, durationSec) {
        await (await this.ensureClient()).longPress(x, y, durationSec);
    }
    async swipe(payload) {
        await (await this.ensureClient()).swipe(payload);
    }
    async typeText(text) {
        await (await this.ensureClient()).typeText(text);
    }
    async clearText() {
        await (await this.ensureClient()).clearText();
    }
    async press(key) {
        await (await this.ensureClient()).press(key);
    }
    async dismissSoftKeyboard() {
        await (await this.ensureClient()).dismissSoftKeyboard();
    }
    async currentApp() {
        return await (await this.ensureClient()).currentApp();
    }
    async windowSize() {
        return await (await this.ensureClient()).windowSize();
    }
    async accessibilityTree() {
        return await (await this.ensureClient()).accessibilityTree();
    }
    async launchApp(bundleId) {
        await withBridgeSpan(this.info.sessionId, 'bridge.app.launch', 'app.launch', { bundle_id: bundleId }, async () => {
            await (await this.ensureClient()).launchApp(bundleId);
        });
    }
    async terminateApp(bundleId) {
        await withBridgeSpan(this.info.sessionId, 'bridge.app.terminate', 'app.terminate', { bundle_id: bundleId }, async () => {
            await (await this.ensureClient()).terminateApp(bundleId);
        });
    }
    async close() {
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
                await this.connectionManager.releaseConnection(this.info.sessionId, this.info.deviceUdid, this.connection.localPort);
                this.connectionReady = false;
                this.connection = null;
            }
        }
        finally {
            logBridgeEvent(this.info.sessionId, 'bridge.session.close.success', {
                phase: 'session.close',
            });
        }
    }
    async ensureClient() {
        if (this.client) {
            return this.client;
        }
        if (!this.connectionReady) {
            this.connection = await this.connectionManager.requestConnection(this.info.sessionId, this.info.deviceUdid, this.info.platformVersion);
            this.connectionReady = true;
            updateSessionDiagnostics(this.info.sessionId, {
                forwarded_port: this.connection.localPort,
                remote_wda_port: this.connection.remotePort,
            });
        }
        this.client = new WdaHttpClient(this.connection.baseUrl, this.info.bundleId, this.info.sessionId);
        return this.client;
    }
}
export class IOSDeviceBridgeSessionManager {
    sessions = new Map();
    connectionManager;
    constructor(options) {
        this.connectionManager =
            options?.connectionManager ?? new WdaConnectionManager();
    }
    async createSession(request) {
        if (!request.device_udid) {
            throw new IOSDeviceBridgeError('invalid_request', 'device_udid is required', 400);
        }
        if (!request.bundle_id) {
            throw new IOSDeviceBridgeError('invalid_request', 'bundle_id is required', 400);
        }
        const info = {
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
        }
        catch (error) {
            logBridgeEvent(info.sessionId, 'bridge.session.create.failure', {
                level: 'error',
                phase: 'session.create',
                ok: false,
                error,
            });
            throw error;
        }
    }
    getSessionInfo(sessionId) {
        return this.getSession(sessionId).sessionInfo();
    }
    async deleteSession(sessionId) {
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
        }
        finally {
            closeSessionDiagnostics(sessionId);
        }
    }
    async closeAll() {
        for (const sessionId of [...this.sessions.keys()]) {
            await this.deleteSession(sessionId);
        }
    }
    async ensureWdaReady(sessionId) {
        const session = this.getSession(sessionId);
        await session.ensureWdaReady();
        return session.sessionInfo();
    }
    getSessionDiagnostics(sessionId) {
        this.getSession(sessionId);
        return getSessionDiagnostics(sessionId);
    }
    async screenshotPngBase64(sessionId) {
        return await this.getSession(sessionId).screenshotPngBase64();
    }
    async tap(sessionId, x, y) {
        await this.getSession(sessionId).tap(x, y);
    }
    async longPress(sessionId, x, y, durationSec) {
        await this.getSession(sessionId).longPress(x, y, durationSec);
    }
    async swipe(sessionId, payload) {
        await this.getSession(sessionId).swipe(payload);
    }
    async typeText(sessionId, text) {
        await this.getSession(sessionId).typeText(text);
    }
    async clearText(sessionId) {
        await this.getSession(sessionId).clearText();
    }
    async press(sessionId, key) {
        await this.getSession(sessionId).press(key);
    }
    async dismissSoftKeyboard(sessionId) {
        await this.getSession(sessionId).dismissSoftKeyboard();
    }
    async currentApp(sessionId) {
        return await this.getSession(sessionId).currentApp();
    }
    async windowSize(sessionId) {
        return await this.getSession(sessionId).windowSize();
    }
    async accessibilityTree(sessionId) {
        return await this.getSession(sessionId).accessibilityTree();
    }
    async launchApp(sessionId, bundleId) {
        await this.getSession(sessionId).launchApp(bundleId);
    }
    async terminateApp(sessionId, bundleId) {
        await this.getSession(sessionId).terminateApp(bundleId);
    }
    getSession(sessionId) {
        const session = this.sessions.get(sessionId);
        if (!session) {
            throw new IOSDeviceBridgeError('session_not_found', `bridge session not found: ${sessionId}`, 404);
        }
        return session;
    }
}
export class WdaBackend extends DeviceSession {
    constructor(_kind, info, _unusedConnectorFactory, _onClose, launcher, connectionManager) {
        super(info, connectionManager ?? new WdaConnectionManager(), launcher ?? createDefaultWdaLauncher(info));
    }
}

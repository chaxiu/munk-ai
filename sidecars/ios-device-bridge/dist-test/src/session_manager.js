import { spawn } from 'node:child_process';
import { randomUUID } from 'node:crypto';
import { createRequire } from 'node:module';
import { createSessionDiagnostics, closeSessionDiagnostics, getSessionDiagnostics, hasSessionDiagnostics, logBridgeEvent, updateSessionDiagnostics, withBridgeSpan, } from './diagnostics.js';
import { IOSDeviceBridgeError } from './errors.js';
import { DEFAULT_WDA_PORT, WdaConnectionManager } from './wda_connection.js';
import { buildWdaCreateSessionPayload, WdaHttpClient } from './wda_http_client.js';
import { createDefaultWdaLauncher, } from './wda_launcher.js';
export { buildWdaCreateSessionPayload };
export { AppiumPreinstalledWdaLauncher } from './wda_launcher.js';
export { WdaConnectionManager } from './wda_connection.js';
const DEFAULT_WDA_BUNDLE_ID = 'sh.munk.wda.xctrunner';
const DEFAULT_DEVICECTEL_DISCOVERY_TIMEOUT_MS = 3000;
const require = createRequire(import.meta.url);
const IOS_DEVICE_UTILITIES = require('appium-ios-device').utilities;
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
export async function listRealDevices(options = {}) {
    const utilities = options.utilities ?? IOS_DEVICE_UTILITIES ?? null;
    const execJsonFn = options.execJsonFn ?? execJson;
    const devicectlTimeoutMs = options.devicectlTimeoutMs ?? DEFAULT_DEVICECTEL_DISCOVERY_TIMEOUT_MS;
    const [appiumDevices, devicectlDevices] = await Promise.all([
        listDevicesViaAppium(utilities),
        listDevicesViaDevicectl(execJsonFn, devicectlTimeoutMs),
    ]);
    const merged = new Map();
    for (const item of devicectlDevices) {
        merged.set(item.udid, { ...item });
    }
    for (const item of appiumDevices) {
        const existing = merged.get(item.udid);
        merged.set(item.udid, {
            ...existing,
            ...item,
            name: item.name || existing?.name || item.udid,
            platform_version: item.platform_version ?? existing?.platform_version ?? null,
            state: item.state ?? existing?.state ?? 'connected',
            appium_visible: true,
            backend_kind: item.backend_kind ??
                existing?.backend_kind ??
                selectBackendKind(item.platform_version ?? existing?.platform_version ?? null),
            coredevice_identifier: existing?.coredevice_identifier ?? item.coredevice_identifier,
        });
    }
    return [...merged.values()]
        .map((item) => {
        const normalizedBackendKind = item.backend_kind ?? selectBackendKind(item.platform_version ?? null);
        return {
            udid: item.udid,
            name: item.name,
            platform_version: item.platform_version,
            state: item.state,
            appium_visible: item.appium_visible,
            backend_kind: normalizedBackendKind,
            ...(item.coredevice_identifier
                ? { coredevice_identifier: item.coredevice_identifier }
                : {}),
        };
    })
        .filter((item) => Boolean(item.udid))
        .sort((left, right) => left.name.localeCompare(right.name) || left.udid.localeCompare(right.udid));
}
export function selectBackendKind(platformVersion) {
    const majorVersion = majorVersionFromString(platformVersion);
    if (majorVersion !== null && majorVersion >= 18) {
        return 'appium_ios_remotexpc';
    }
    return 'appium_ios_device';
}
function majorVersionFromString(version) {
    if (!version) {
        return null;
    }
    const segment = version.split('.', 1)[0]?.trim();
    if (!segment) {
        return null;
    }
    const parsed = Number.parseInt(segment, 10);
    return Number.isFinite(parsed) ? parsed : null;
}
async function listDevicesViaAppium(utilities) {
    if (!utilities) {
        return [];
    }
    let udids = [];
    try {
        udids = await utilities.getConnectedDevices();
    }
    catch {
        return [];
    }
    return Promise.all(udids.map(async (udid) => {
        const [nameResult, versionResult] = await Promise.allSettled([
            utilities.getDeviceName(udid),
            utilities.getOSVersion(udid),
        ]);
        const platformVersion = versionResult.status === 'fulfilled' ? versionResult.value : null;
        return {
            udid,
            name: nameResult.status === 'fulfilled' && nameResult.value
                ? nameResult.value
                : udid,
            platform_version: platformVersion,
            state: 'connected',
            appium_visible: true,
            backend_kind: selectBackendKind(platformVersion),
        };
    }));
}
async function listDevicesViaDevicectl(execJsonFn, timeoutMs) {
    let output;
    try {
        output = await execJsonFn(['xcrun', 'devicectl', 'list', 'devices', '--quiet', '--json-output', '-'], timeoutMs);
    }
    catch {
        return [];
    }
    return findDeviceEntries(output)
        .map((item) => {
        const udid = lookup(item, 'hardwareProperties.udid', 'udid') ?? '';
        const platformVersion = lookup(item, 'deviceProperties.osVersionNumber', 'deviceProperties.osVersion');
        return {
            udid,
            name: lookup(item, 'deviceProperties.name', 'name') ?? udid,
            platform_version: platformVersion,
            state: lookup(item, 'connectionProperties.state', 'connectionProperties.tunnelState', 'state'),
            appium_visible: false,
            backend_kind: selectBackendKind(platformVersion),
            coredevice_identifier: lookup(item, 'identifier'),
        };
    })
        .filter((item) => item.udid);
}
async function execJson(command, timeoutMs) {
    const text = await exec(command, timeoutMs);
    const loaded = JSON.parse(text);
    return typeof loaded === 'object' && loaded
        ? loaded
        : {};
}
async function exec(command, timeoutMs) {
    return await new Promise((resolve, reject) => {
        const spawnOptions = resolveSpawnOptions(command);
        const child = spawn(command[0], command.slice(1), {
            stdio: ['ignore', 'pipe', 'pipe'],
            ...spawnOptions,
        });
        let settled = false;
        let timeoutHandle = null;
        let stdout = '';
        let stderr = '';
        const finalize = (callback) => {
            if (settled) {
                return;
            }
            settled = true;
            if (timeoutHandle) {
                clearTimeout(timeoutHandle);
            }
            callback();
        };
        if (timeoutMs && timeoutMs > 0) {
            timeoutHandle = setTimeout(() => {
                if (!settled) {
                    child.kill('SIGKILL');
                    finalize(() => reject(new Error(`command timed out after ${timeoutMs}ms: ${command.join(' ')}`)));
                }
            }, timeoutMs);
        }
        child.stdout.on('data', (chunk) => {
            stdout += String(chunk);
        });
        child.stderr.on('data', (chunk) => {
            stderr += String(chunk);
        });
        child.on('error', (error) => finalize(() => reject(error)));
        child.on('close', (code) => {
            finalize(() => {
                if (code === 0) {
                    resolve(stdout);
                    return;
                }
                reject(new Error(`command failed (${code}): ${command.join(' ')}\n${stderr || stdout}`.trim()));
            });
        });
    });
}
function resolveSpawnOptions(command) {
    if (!shouldRunDevicectlAsOriginalUser(command)) {
        return {};
    }
    const uid = Number.parseInt(process.env.SUDO_UID ?? '', 10);
    const gid = Number.parseInt(process.env.SUDO_GID ?? '', 10);
    if (!Number.isFinite(uid) || !Number.isFinite(gid)) {
        return {};
    }
    const env = { ...process.env };
    if (process.env.SUDO_USER) {
        env.USER = process.env.SUDO_USER;
        env.LOGNAME = process.env.SUDO_USER;
    }
    return { uid, gid, env };
}
function shouldRunDevicectlAsOriginalUser(command) {
    return (typeof process.getuid === 'function' &&
        process.getuid() === 0 &&
        command[0] === 'xcrun' &&
        command[1] === 'devicectl' &&
        Boolean(process.env.SUDO_UID) &&
        Boolean(process.env.SUDO_GID));
}
function findDeviceEntries(payload) {
    const results = [];
    const stack = [payload];
    while (stack.length > 0) {
        const current = stack.pop();
        if (Array.isArray(current)) {
            stack.push(...current);
            continue;
        }
        if (!current || typeof current !== 'object') {
            continue;
        }
        const mapping = current;
        if (lookup(mapping, 'hardwareProperties.udid', 'udid') &&
            lookup(mapping, 'deviceProperties.name', 'name')) {
            results.push(mapping);
        }
        stack.push(...Object.values(mapping));
    }
    return results;
}
function lookup(mapping, ...paths) {
    for (const path of paths) {
        let current = mapping;
        for (const segment of path.split('.')) {
            if (!current || typeof current !== 'object' || Array.isArray(current)) {
                current = undefined;
                break;
            }
            current = current[segment];
        }
        if (typeof current === 'string' && current) {
            return current;
        }
    }
    return null;
}

import * as assert from 'node:assert';
import * as fs from 'node:fs';
import * as os from 'node:os';
import * as path from 'node:path';
import { test } from 'node:test';
import Fastify from 'fastify';
import bridgeRoutes from '../src/routes/bridge.js';
import { normalizeForDiagnostics } from '../src/diagnostics.js';
import { AppiumPreinstalledWdaLauncher, IOSDeviceBridgeSessionManager, buildWdaCreateSessionPayload, listRealDevices, WdaBackend, } from '../src/session_manager.js';
import { IOSDeviceBridgeError } from '../src/errors.js';
test('healthz route returns lifecycle metadata', async () => {
    process.env.MUNK_BRIDGE_MANAGER_TOKEN = 'test-token';
    process.env.MUNK_PARENT_PID = '12345';
    const server = Fastify();
    await server.register(bridgeRoutes);
    try {
        const response = await server.inject({ url: '/healthz' });
        const payload = response.json();
        assert.equal(payload.status, 'ok');
        assert.equal(payload.managerToken, 'test-token');
        assert.equal(payload.parentPid, '12345');
        assert.equal(typeof payload.pid, 'number');
        assert.equal(typeof payload.startedAt, 'string');
    }
    finally {
        delete process.env.MUNK_BRIDGE_MANAGER_TOKEN;
        delete process.env.MUNK_PARENT_PID;
        await server.close();
    }
});
test('createSession stores and exposes a session', async () => {
    const manager = new IOSDeviceBridgeSessionManager();
    const session = await manager.createSession({
        device_udid: 'device-1',
        bundle_id: 'com.example.todo',
        platform_version: '16.7',
    });
    const loaded = manager.getSessionInfo(session.sessionId);
    assert.equal(loaded.deviceUdid, 'device-1');
    assert.equal(loaded.bundleId, 'com.example.todo');
    assert.equal(loaded.backendKind, 'appium_ios_device');
    await manager.deleteSession(session.sessionId);
});
test('createSession writes diagnostics files and redacts sensitive fields', async () => {
    const runDir = fs.mkdtempSync(path.join(os.tmpdir(), 'ios-bridge-diag-'));
    const manager = new IOSDeviceBridgeSessionManager();
    const session = await manager.createSession({
        device_udid: 'device-1',
        bundle_id: 'com.example.todo',
        platform_version: '16.7',
        diagnostics: {
            operation_id: 'op-1',
            run_dir: runDir,
            app_id: 'app-1',
            plan_id: 'plan-1',
            case_id: 'case-1',
        },
    });
    const diagnostics = manager.getSessionDiagnostics(session.sessionId);
    assert.equal(diagnostics.events_path, path.join(runDir, 'ios_bridge', 'events.jsonl'));
    assert.equal(fs.existsSync(path.join(runDir, 'ios_bridge', 'session.json')), true);
    assert.equal(fs.existsSync(path.join(runDir, 'ios_bridge', 'summary.json')), true);
    assert.equal(fs.existsSync(path.join(runDir, 'ios_bridge', 'events.jsonl')), true);
    const events = fs.readFileSync(path.join(runDir, 'ios_bridge', 'events.jsonl'), 'utf8');
    assert.match(events, /bridge\.session\.create\.success/);
    assert.match(events, /"operation_id":"op-1"/);
    const summary = JSON.parse(fs.readFileSync(path.join(runDir, 'ios_bridge', 'summary.json'), 'utf8'));
    assert.equal(summary.context.operation_id, 'op-1');
    assert.equal(summary.last_phase, 'session.create');
    assert.deepEqual(normalizeForDiagnostics({
        sudo_password: 'secret-pass',
        nested: { api_key: 'secret-key', value: 'kept' },
    }), {
        sudo_password: '<redacted>',
        nested: { api_key: '<redacted>', value: 'kept' },
    });
    await manager.deleteSession(session.sessionId);
});
test('createSession for iOS 18 selects remotexpc backend kind metadata', async () => {
    const manager = new IOSDeviceBridgeSessionManager();
    const session = await manager.createSession({
        device_udid: 'device-18',
        bundle_id: 'com.example.todo',
        platform_version: '18.6.2',
    });
    assert.equal(session.backendKind, 'appium_ios_remotexpc');
    await manager.deleteSession(session.sessionId);
});
test('listRealDevices merges Appium devices with devicectl enrichment', async () => {
    const devices = await listRealDevices({
        utilities: {
            async getConnectedDevices() {
                return ['real-1-udid'];
            },
            async getDeviceName(udid) {
                assert.equal(udid, 'real-1-udid');
                return 'Zhutao iPhone';
            },
            async getOSVersion(udid) {
                assert.equal(udid, 'real-1-udid');
                return '18.6.2';
            },
        },
        async execJsonFn() {
            return {
                result: {
                    devices: [
                        {
                            identifier: 'real-1',
                            deviceProperties: { name: 'Zhutao iPhone', osVersionNumber: '18.6.2' },
                            hardwareProperties: { udid: 'real-1-udid' },
                            connectionProperties: { state: 'connected' },
                        },
                        {
                            identifier: 'real-2',
                            deviceProperties: { name: 'Remote iPhone', osVersionNumber: '18.5' },
                            hardwareProperties: { udid: 'real-2-udid' },
                            connectionProperties: { state: 'connected' },
                        },
                    ],
                },
            };
        },
    });
    assert.deepEqual(devices, [
        {
            udid: 'real-2-udid',
            name: 'Remote iPhone',
            platform_version: '18.5',
            state: 'connected',
            appium_visible: false,
            backend_kind: 'appium_ios_remotexpc',
            coredevice_identifier: 'real-2',
        },
        {
            udid: 'real-1-udid',
            name: 'Zhutao iPhone',
            platform_version: '18.6.2',
            state: 'connected',
            appium_visible: true,
            backend_kind: 'appium_ios_remotexpc',
            coredevice_identifier: 'real-1',
        },
    ]);
});
test('listRealDevices returns Appium devices when devicectl times out', async () => {
    const devices = await listRealDevices({
        utilities: {
            async getConnectedDevices() {
                return ['legacy-udid'];
            },
            async getDeviceName() {
                return 'Legacy iPhone';
            },
            async getOSVersion() {
                return '16.7';
            },
        },
        async execJsonFn() {
            throw new Error('timed out');
        },
    });
    assert.deepEqual(devices, [
        {
            udid: 'legacy-udid',
            name: 'Legacy iPhone',
            platform_version: '16.7',
            state: 'connected',
            appium_visible: true,
            backend_kind: 'appium_ios_device',
        },
    ]);
});
test('ensureWdaReady falls back to launch when status probe is a false positive', async () => {
    const info = {
        sessionId: 'session-1',
        deviceUdid: 'device-18',
        bundleId: 'com.example.todo',
        wdaBundleId: 'sh.munk.wda.xctrunner',
        platformVersion: '18.6.2',
        backendKind: 'appium_ios_remotexpc',
    };
    const launchCalls = [];
    let probeCalls = 0;
    let ensureCalls = 0;
    const connection = {
        localPort: 8100,
        remotePort: 8100,
        baseUrl: 'http://127.0.0.1:8100',
    };
    const backend = new WdaBackend('appium_ios_remotexpc', info, undefined, undefined, {
        launchAndWaitReady: async (client, conn) => {
            launchCalls.push({ client, conn });
            if (await client.probeStatus()) {
                try {
                    await client.ensureReady();
                    return;
                }
                catch { }
            }
            await client.ensureReady();
        },
        close: async () => { },
    });
    const client = {
        probeStatus: async () => {
            probeCalls += 1;
            return true;
        },
        ensureReady: async () => {
            ensureCalls += 1;
            if (ensureCalls === 1) {
                throw new IOSDeviceBridgeError('wda_invalid_response', 'WDA create session response missing sessionId', 502);
            }
        },
    };
    backend.ensureClient = async () => client;
    backend.connection = connection;
    await backend.ensureWdaReady();
    assert.equal(probeCalls, 1);
    assert.equal(ensureCalls, 2);
    assert.equal(launchCalls.length, 1);
});
test('buildWdaCreateSessionPayload matches Appium WDA session shape', () => {
    assert.deepEqual(buildWdaCreateSessionPayload('com.example.todo'), {
        capabilities: {
            firstMatch: [
                {
                    bundleId: 'com.example.todo',
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
    });
});
test('AppiumPreinstalledWdaLauncher retries once after Code=41 and then succeeds', async () => {
    const info = {
        sessionId: 'session-2',
        deviceUdid: 'device-18',
        bundleId: 'com.example.todo',
        wdaBundleId: 'sh.munk.wda.xctrunner',
        platformVersion: '18.6.2',
        backendKind: 'appium_ios_remotexpc',
    };
    const launchSessionIds = [];
    const delayCalls = [];
    let quitCalls = 0;
    let ensureCalls = 0;
    let closeCalls = 0;
    const launcher = new AppiumPreinstalledWdaLauncher(info, (_sessionInfo, _localPort) => ({
        async launchWithPreinstalledWDA(sessionId) {
            launchSessionIds.push(sessionId);
            return null;
        },
        async quit() {
            quitCalls += 1;
        },
    }), async (ms) => {
        delayCalls.push(ms);
    });
    const client = {
        async probeStatus() {
            return false;
        },
        async ensureReady() {
            ensureCalls += 1;
            if (ensureCalls === 1) {
                throw new IOSDeviceBridgeError('wda_ui_testing_not_authorized', 'Error Domain=XCTDaemonErrorDomain Code=41 "Not authorized for performing UI testing actions."', 502, {
                    response_payload: {
                        value: {
                            error: 'session not created',
                            message: 'Error Domain=XCTDaemonErrorDomain Code=41 "Not authorized for performing UI testing actions."',
                        },
                    },
                });
            }
        },
        async close() {
            closeCalls += 1;
        },
    };
    await launcher.launchAndWaitReady(client, {
        localPort: 8100,
        remotePort: 8100,
        baseUrl: 'http://127.0.0.1:8100',
    });
    assert.equal(ensureCalls, 2);
    assert.equal(closeCalls, 1);
    assert.equal(quitCalls, 1);
    assert.deepEqual(delayCalls, [3000]);
    assert.deepEqual(launchSessionIds, [
        'session-2-wda-attempt-1',
        'session-2-wda-attempt-2',
    ]);
});
test('AppiumPreinstalledWdaLauncher reuses an already reachable WDA', async () => {
    const info = {
        sessionId: 'session-reuse',
        deviceUdid: 'device-18',
        bundleId: 'com.example.todo',
        wdaBundleId: 'sh.munk.wda.xctrunner',
        platformVersion: '18.6.2',
        backendKind: 'appium_ios_remotexpc',
    };
    let launchCalls = 0;
    let probeCalls = 0;
    let ensureCalls = 0;
    const launcher = new AppiumPreinstalledWdaLauncher(info, () => ({
        async launchWithPreinstalledWDA() {
            launchCalls += 1;
            return null;
        },
        async quit() { },
    }), async () => { });
    await launcher.launchAndWaitReady({
        async probeStatus() {
            probeCalls += 1;
            return true;
        },
        async ensureReady() {
            ensureCalls += 1;
        },
        async close() { },
    }, {
        localPort: 8100,
        remotePort: 8100,
        baseUrl: 'http://127.0.0.1:8100',
    });
    assert.equal(probeCalls, 1);
    assert.equal(ensureCalls, 1);
    assert.equal(launchCalls, 0);
});
test('AppiumPreinstalledWdaLauncher returns actionable unlock error after repeated Code=41', async () => {
    const info = {
        sessionId: 'session-3',
        deviceUdid: 'device-18',
        bundleId: 'com.example.todo',
        wdaBundleId: 'sh.munk.wda.xctrunner',
        platformVersion: '18.6.2',
        backendKind: 'appium_ios_remotexpc',
    };
    let quitCalls = 0;
    const launcher = new AppiumPreinstalledWdaLauncher(info, () => ({
        async launchWithPreinstalledWDA() {
            return null;
        },
        async quit() {
            quitCalls += 1;
        },
    }), async () => { });
    const code41 = new IOSDeviceBridgeError('wda_ui_testing_not_authorized', 'Error Domain=XCTDaemonErrorDomain Code=41 "Not authorized for performing UI testing actions."', 502, {
        response_payload: {
            value: {
                error: 'session not created',
                message: 'Error Domain=XCTDaemonErrorDomain Code=41 "Not authorized for performing UI testing actions."',
            },
        },
    });
    await assert.rejects(launcher.launchAndWaitReady({
        async probeStatus() {
            return false;
        },
        async ensureReady() {
            throw code41;
        },
        async close() { },
    }, {
        localPort: 8100,
        remotePort: 8100,
        baseUrl: 'http://127.0.0.1:8100',
    }), (error) => {
        assert.ok(error instanceof IOSDeviceBridgeError);
        assert.equal(error.code, 'wda_ui_testing_not_authorized');
        assert.match(error.message, /Wake and unlock the device/i);
        assert.equal(error.details?.needs_device_unlock, true);
        assert.equal(error.details?.attempt_count, 2);
        return true;
    });
    assert.equal(quitCalls, 1);
});

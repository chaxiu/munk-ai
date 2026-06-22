import axios, {} from 'axios';
import { buildAccessibilityTreePayload, buildCurrentAppPayload, } from './device_payloads.js';
import { logBridgeEvent, normalizeForDiagnostics, updateSessionDiagnostics, } from './diagnostics.js';
import { IOSDeviceBridgeError } from './errors.js';
const WDA_UI_TESTING_AUTHORIZATION_PATTERNS = [
    'xctdaemonerrordomain code=41',
    'not authorized for performing ui testing actions',
];
export class WdaHttpClient {
    baseUrl;
    bundleId;
    diagnosticsSessionId;
    sessionId = null;
    constructor(baseUrl, bundleId, diagnosticsSessionId) {
        this.baseUrl = baseUrl.replace(/\/$/, '');
        this.bundleId = bundleId;
        this.diagnosticsSessionId = diagnosticsSessionId;
    }
    async probeStatus() {
        try {
            await this.request('GET', '/status');
            return true;
        }
        catch {
            return false;
        }
    }
    async ensureReady() {
        await this.ensureSessionId();
    }
    async screenshotPngBase64() {
        const payload = await this.request('GET', '/screenshot');
        const value = payload.value;
        if (typeof value !== 'string' || !value) {
            throw new IOSDeviceBridgeError('wda_invalid_response', 'WDA screenshot response missing base64 payload', 502);
        }
        return value;
    }
    async tap(x, y) {
        await this.sessionRequest('POST', '/wda/tap', { x, y });
    }
    async longPress(x, y, durationSec) {
        await this.sessionRequest('POST', '/wda/touchAndHold', {
            x,
            y,
            duration: durationSec ?? 1.0,
        });
    }
    async swipe(payload) {
        const body = {
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
    async typeText(text) {
        await this.sessionRequest('POST', '/wda/keys', { value: Array.from(text) });
    }
    async clearText() {
        const payload = await this.sessionRequest('GET', '/element/active');
        const value = payload.value;
        if (!value || typeof value !== 'object') {
            throw new IOSDeviceBridgeError('wda_invalid_response', 'WDA active element response missing value object', 502);
        }
        const mapping = value;
        const elementId = (typeof mapping['element-6066-11e4-a52e-4f735466cecf'] === 'string'
            ? mapping['element-6066-11e4-a52e-4f735466cecf']
            : null) ??
            (typeof mapping.ELEMENT === 'string' ? mapping.ELEMENT : null);
        if (!elementId) {
            throw new IOSDeviceBridgeError('wda_invalid_response', 'WDA active element response missing element identifier', 502);
        }
        await this.sessionRequest('POST', `/element/${elementId}/clear`);
    }
    async press(key) {
        const normalized = key.trim().toLowerCase();
        if (normalized === 'home') {
            await this.request('POST', '/wda/homescreen');
            return;
        }
        await this.sessionRequest('POST', '/wda/keys', { value: [key] });
    }
    async dismissSoftKeyboard() {
        await this.sessionRequest('POST', '/wda/keyboard/dismiss', { keyNames: [] }, true);
    }
    async currentApp() {
        const payload = await this.request('GET', '/wda/activeAppInfo');
        return buildCurrentAppPayload(payload.value);
    }
    async windowSize() {
        const payload = await this.request('GET', '/window/size');
        if (!payload.value || typeof payload.value !== 'object') {
            throw new IOSDeviceBridgeError('wda_invalid_response', 'WDA window size response missing value object', 502);
        }
        const value = payload.value;
        return {
            width: Number(value.width ?? 0),
            height: Number(value.height ?? 0),
        };
    }
    async accessibilityTree() {
        const payload = await this.request('GET', '/source?format=json');
        return buildAccessibilityTreePayload(payload.value);
    }
    async launchApp(bundleId) {
        updateSessionDiagnostics(this.diagnosticsSessionId, {
            app_launch_attempted: true,
            last_app_launch_bundle_id: bundleId,
        });
        await this.sessionRequest('POST', '/wda/apps/launch', { bundleId });
    }
    async terminateApp(bundleId) {
        await this.sessionRequest('POST', '/wda/apps/terminate', { bundleId });
    }
    async close() {
        if (!this.sessionId) {
            return;
        }
        const sessionId = this.sessionId;
        this.sessionId = null;
        try {
            await this.request('DELETE', `/session/${sessionId}`);
        }
        catch {
            // Best-effort teardown.
        }
    }
    async sessionRequest(method, route, body, allowError = false) {
        const sessionId = await this.ensureSessionId();
        return await this.request(method, `/session/${sessionId}${route}`, body, allowError);
    }
    async ensureSessionId() {
        if (this.sessionId) {
            return this.sessionId;
        }
        const sessionPayload = buildWdaCreateSessionPayload(this.bundleId);
        let responseStatus = null;
        let payload = {};
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
            const response = await axios.request({
                method: 'POST',
                url: `${this.baseUrl}/session`,
                data: sessionPayload,
                timeout: 10000,
                validateStatus: () => true,
            });
            responseStatus = response.status;
            payload = response.data ?? {};
        }
        catch (error) {
            if (axios.isAxiosError(error)) {
                logBridgeEvent(this.diagnosticsSessionId, 'bridge.wda.session.create.failure', {
                    level: 'error',
                    phase: 'wda.session',
                    ok: false,
                    duration_ms: Date.now() - start,
                    error,
                });
                throw new IOSDeviceBridgeError('wda_request_failed', `WDA request failed for POST /session: ${error.message}`, 502);
            }
            throw new IOSDeviceBridgeError('wda_request_failed', `WDA request failed for POST /session: ${error instanceof Error ? error.message : String(error)}`, 502);
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
                details: { responseStatus, wdaSessionId: sessionId },
            });
            return sessionId;
        }
        if (isWdaUiTestingAuthorizationPayload(payload)) {
            throw new IOSDeviceBridgeError('wda_ui_testing_not_authorized', 'WDA started but iOS rejected UI testing actions. Unlock or wake the device and retry.', 502, { needs_device_unlock: true, response_status: responseStatus, response_payload: payload });
        }
        if (responseStatus !== null && responseStatus >= 400) {
            const payloadMessage = lookup(payload, 'value.message', 'message');
            throw new IOSDeviceBridgeError('wda_request_failed', payloadMessage
                ? `WDA request failed for POST /session: ${payloadMessage}`
                : `WDA request failed for POST /session: HTTP ${responseStatus}`, 502);
        }
        throw new IOSDeviceBridgeError('wda_invalid_response', 'WDA create session response missing sessionId', 502, { response_payload: payload });
    }
    async request(method, path, body, allowError = false) {
        const start = Date.now();
        logBridgeEvent(this.diagnosticsSessionId, 'bridge.wda.http.request', {
            level: 'debug',
            phase: `wda.http ${method} ${path}`,
            details: { method, path, baseUrl: this.baseUrl, requestBody: body ?? null },
        });
        try {
            const response = await axios.request({
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
                details: { method, path, status: response.status },
            });
            if (allowError && response.status >= 400) {
                return {};
            }
            return response.data ?? {};
        }
        catch (error) {
            logBridgeEvent(this.diagnosticsSessionId, 'bridge.wda.http.error', {
                level: 'error',
                phase: `wda.http ${method} ${path}`,
                ok: false,
                duration_ms: Date.now() - start,
                error,
            });
            throw new IOSDeviceBridgeError('wda_request_failed', `WDA request failed for ${method} ${path}: ${error instanceof Error ? error.message : String(error)}`, 502);
        }
    }
}
export function buildWdaCreateSessionPayload(bundleId) {
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
function extractWdaSessionId(payload) {
    const direct = typeof payload.sessionId === 'string' ? payload.sessionId : null;
    const nested = payload.value &&
        typeof payload.value === 'object' &&
        typeof payload.value.sessionId === 'string'
        ? payload.value.sessionId
        : null;
    return direct ?? nested;
}
function isWdaUiTestingAuthorizationPayload(payload) {
    if (!payload) {
        return false;
    }
    const serialized = JSON.stringify(normalizeForDiagnostics(payload)).toLowerCase();
    return WDA_UI_TESTING_AUTHORIZATION_PATTERNS.every((pattern) => serialized.includes(pattern));
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
export { isWdaUiTestingAuthorizationPayload };

import { IOSDeviceBridgeError } from './errors.js';
export function buildCurrentAppPayload(rawValue) {
    const raw = asRecord(rawValue);
    return {
        bundle_id: readOptionalString(raw.bundleId),
        name: readOptionalString(raw.name),
        pid: readOptionalNumber(raw.pid),
        raw,
    };
}
export function buildAccessibilityTreePayload(rawValue) {
    if (rawValue === null || rawValue === undefined) {
        return null;
    }
    const root = buildAccessibilityNodePayload(rawValue, 'root');
    return { root };
}
function buildAccessibilityNodePayload(rawValue, path) {
    const raw = asRecord(rawValue, path);
    const rawChildren = raw.children;
    const children = Array.isArray(rawChildren)
        ? rawChildren.map((child, index) => buildAccessibilityNodePayload(child, `${path}.children[${index}]`))
        : [];
    return {
        type: readOptionalString(raw.type),
        name: readOptionalString(raw.name),
        label: readOptionalString(raw.label),
        value: readOptionalPrimitive(raw.value),
        identifier: readOptionalString(raw.identifier),
        bundle_id: readOptionalString(raw.bundleId),
        enabled: readOptionalBoolean(raw.enabled),
        visible: readOptionalBoolean(raw.visible),
        accessible: readOptionalBoolean(raw.accessible),
        focused: readOptionalBoolean(raw.focused),
        selected: readOptionalBoolean(raw.selected),
        rect: readOptionalRect(raw.rect, `${path}.rect`),
        native_frame: readOptionalString(raw.nativeFrame),
        frame: readOptionalString(raw.frame),
        children,
    };
}
function readOptionalRect(value, path) {
    if (value === null || value === undefined) {
        return null;
    }
    const rect = asRecord(value, path);
    const x = readRequiredNumber(rect.x, `${path}.x`);
    const y = readRequiredNumber(rect.y, `${path}.y`);
    const width = readRequiredNumber(rect.width, `${path}.width`);
    const height = readRequiredNumber(rect.height, `${path}.height`);
    return { x, y, width, height };
}
function asRecord(value, path = 'payload') {
    if (typeof value !== 'object' || value === null || Array.isArray(value)) {
        throw new IOSDeviceBridgeError('wda_invalid_response', `WDA ${path} response must be an object`, 502);
    }
    return value;
}
function readOptionalPrimitive(value) {
    if (typeof value === 'string' ||
        typeof value === 'number' ||
        typeof value === 'boolean') {
        return value;
    }
    return null;
}
function readOptionalString(value) {
    return typeof value === 'string' && value ? value : null;
}
function readOptionalBoolean(value) {
    return typeof value === 'boolean' ? value : null;
}
function readOptionalNumber(value) {
    return typeof value === 'number' && Number.isFinite(value) ? value : null;
}
function readRequiredNumber(value, path) {
    if (typeof value === 'number' && Number.isFinite(value)) {
        return value;
    }
    throw new IOSDeviceBridgeError('wda_invalid_response', `WDA ${path} must be a finite number`, 502);
}

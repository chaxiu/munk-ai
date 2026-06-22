import {IOSDeviceBridgeError} from './errors.js';

export interface BridgeCurrentAppPayload {
  bundle_id: string | null;
  name: string | null;
  pid: number | null;
  raw: Record<string, unknown>;
}

export interface BridgeAccessibilityRectPayload {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface BridgeAccessibilityNodePayload {
  type: string | null;
  name: string | null;
  label: string | null;
  value: string | number | boolean | null;
  identifier: string | null;
  bundle_id: string | null;
  enabled: boolean | null;
  visible: boolean | null;
  accessible: boolean | null;
  focused: boolean | null;
  selected: boolean | null;
  rect: BridgeAccessibilityRectPayload | null;
  native_frame: string | null;
  frame: string | null;
  children: BridgeAccessibilityNodePayload[];
}

export interface BridgeAccessibilityTreePayload {
  root: BridgeAccessibilityNodePayload;
}

export function buildCurrentAppPayload(
  rawValue: unknown,
): BridgeCurrentAppPayload {
  const raw = asRecord(rawValue);
  return {
    bundle_id: readOptionalString(raw.bundleId),
    name: readOptionalString(raw.name),
    pid: readOptionalNumber(raw.pid),
    raw,
  };
}

export function buildAccessibilityTreePayload(
  rawValue: unknown,
): BridgeAccessibilityTreePayload | null {
  if (rawValue === null || rawValue === undefined) {
    return null;
  }
  const root = buildAccessibilityNodePayload(rawValue, 'root');
  return {root};
}

function buildAccessibilityNodePayload(
  rawValue: unknown,
  path: string,
): BridgeAccessibilityNodePayload {
  const raw = asRecord(rawValue, path);
  const rawChildren = raw.children;
  const children = Array.isArray(rawChildren)
    ? rawChildren.map((child, index) =>
        buildAccessibilityNodePayload(child, `${path}.children[${index}]`),
      )
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

function readOptionalRect(
  value: unknown,
  path: string,
): BridgeAccessibilityRectPayload | null {
  if (value === null || value === undefined) {
    return null;
  }
  const rect = asRecord(value, path);
  const x = readRequiredNumber(rect.x, `${path}.x`);
  const y = readRequiredNumber(rect.y, `${path}.y`);
  const width = readRequiredNumber(rect.width, `${path}.width`);
  const height = readRequiredNumber(rect.height, `${path}.height`);
  return {x, y, width, height};
}

function asRecord(
  value: unknown,
  path = 'payload',
): Record<string, unknown> {
  if (typeof value !== 'object' || value === null || Array.isArray(value)) {
    throw new IOSDeviceBridgeError(
      'wda_invalid_response',
      `WDA ${path} response must be an object`,
      502,
    );
  }
  return value as Record<string, unknown>;
}

function readOptionalPrimitive(
  value: unknown,
): string | number | boolean | null {
  if (
    typeof value === 'string' ||
    typeof value === 'number' ||
    typeof value === 'boolean'
  ) {
    return value;
  }
  return null;
}

function readOptionalString(value: unknown): string | null {
  return typeof value === 'string' && value ? value : null;
}

function readOptionalBoolean(value: unknown): boolean | null {
  return typeof value === 'boolean' ? value : null;
}

function readOptionalNumber(value: unknown): number | null {
  return typeof value === 'number' && Number.isFinite(value) ? value : null;
}

function readRequiredNumber(value: unknown, path: string): number {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return value;
  }
  throw new IOSDeviceBridgeError(
    'wda_invalid_response',
    `WDA ${path} must be a finite number`,
    502,
  );
}

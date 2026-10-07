import {spawn} from 'node:child_process';
import type {SpawnOptions} from 'node:child_process';
import {createRequire} from 'node:module';

import type {DeviceBackendKind, DeviceInfo} from './session_types.js';

const DEFAULT_DEVICECTEL_DISCOVERY_TIMEOUT_MS = 3000;

const require = createRequire(import.meta.url);
const IOS_DEVICE_UTILITIES = (require('appium-ios-device') as {
  utilities?: IOSDeviceUtilitiesLike;
}).utilities;

interface IOSDeviceUtilitiesLike {
  getConnectedDevices(): Promise<string[]>;
  getDeviceName(udid: string): Promise<string>;
  getOSVersion(udid: string): Promise<string>;
}

export async function listRealDevices(
  options: {
    utilities?: IOSDeviceUtilitiesLike | null;
    execJsonFn?: (
      command: string[],
      timeoutMs?: number,
    ) => Promise<Record<string, unknown>>;
    devicectlTimeoutMs?: number;
  } = {},
): Promise<DeviceInfo[]> {
  const utilities = options.utilities ?? IOS_DEVICE_UTILITIES ?? null;
  const execJsonFn = options.execJsonFn ?? execJson;
  const devicectlTimeoutMs =
    options.devicectlTimeoutMs ?? DEFAULT_DEVICECTEL_DISCOVERY_TIMEOUT_MS;
  const [appiumDevices, devicectlDevices] = await Promise.all([
    listDevicesViaAppium(utilities),
    listDevicesViaDevicectl(execJsonFn, devicectlTimeoutMs),
  ]);
  return mergeDiscoveredDevices(appiumDevices, devicectlDevices)
    .map(normalizeDeviceInfo)
    .filter(hasDeviceUdid)
    .sort(compareDeviceInfo);
}

export function selectBackendKind(
  platformVersion: string | null,
): DeviceBackendKind {
  const majorVersion = majorVersionFromString(platformVersion);
  if (majorVersion !== null && majorVersion >= 18) {
    return 'appium_ios_remotexpc';
  }
  return 'appium_ios_device';
}

function majorVersionFromString(version: string | null | undefined): number | null {
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

async function listDevicesViaAppium(
  utilities: IOSDeviceUtilitiesLike | null,
): Promise<DeviceInfo[]> {
  if (!utilities) {
    return [];
  }
  let udids: string[] = [];
  try {
    udids = await utilities.getConnectedDevices();
  } catch {
    return [];
  }
  return Promise.all(
    udids.map(async (udid) => {
      const [nameResult, versionResult] = await Promise.allSettled([
        utilities.getDeviceName(udid),
        utilities.getOSVersion(udid),
      ]);
      const platformVersion =
        versionResult.status === 'fulfilled' ? versionResult.value : null;
      return {
        udid,
        name:
          nameResult.status === 'fulfilled' && nameResult.value
            ? nameResult.value
            : udid,
        platform_version: platformVersion,
        state: 'connected',
        appium_visible: true,
        backend_kind: selectBackendKind(platformVersion),
      } satisfies DeviceInfo;
    }),
  );
}

async function listDevicesViaDevicectl(
  execJsonFn: (
    command: string[],
    timeoutMs?: number,
  ) => Promise<Record<string, unknown>>,
  timeoutMs: number,
): Promise<DeviceInfo[]> {
  let output: Record<string, unknown>;
  try {
    output = await execJsonFn(
      ['xcrun', 'devicectl', 'list', 'devices', '--quiet', '--json-output', '-'],
      timeoutMs,
    );
  } catch {
    return [];
  }
  return findDeviceEntries(output)
    .map((item) => {
      const udid = lookup(item, 'hardwareProperties.udid', 'udid') ?? '';
      const platformVersion = lookup(
        item,
        'deviceProperties.osVersionNumber',
        'deviceProperties.osVersion',
      );
      return {
        udid,
        name: lookup(item, 'deviceProperties.name', 'name') ?? udid,
        platform_version: platformVersion,
        state: lookup(
          item,
          'connectionProperties.state',
          'connectionProperties.tunnelState',
          'state',
        ),
        appium_visible: false,
        backend_kind: selectBackendKind(platformVersion),
        coredevice_identifier: lookup(item, 'identifier'),
      } satisfies DeviceInfo;
    })
    .filter(hasDeviceUdid);
}

function mergeDiscoveredDevices(
  appiumDevices: DeviceInfo[],
  devicectlDevices: DeviceInfo[],
): DeviceInfo[] {
  const merged = new Map<string, DeviceInfo>();
  for (const item of devicectlDevices) {
    merged.set(item.udid, {...item});
  }
  for (const item of appiumDevices) {
    merged.set(item.udid, mergeAppiumDevice(merged.get(item.udid), item));
  }
  return [...merged.values()];
}

function mergeAppiumDevice(
  existing: DeviceInfo | undefined,
  item: DeviceInfo,
): DeviceInfo {
  const platformVersion = item.platform_version ?? existing?.platform_version ?? null;
  return {
    ...existing,
    ...item,
    name: item.name || existing?.name || item.udid,
    platform_version: platformVersion,
    state: item.state ?? existing?.state ?? 'connected',
    appium_visible: true,
    backend_kind:
      item.backend_kind ??
      existing?.backend_kind ??
      selectBackendKind(platformVersion),
    coredevice_identifier:
      existing?.coredevice_identifier ?? item.coredevice_identifier,
  };
}

function normalizeDeviceInfo(item: DeviceInfo): DeviceInfo {
  const normalizedBackendKind =
    item.backend_kind ?? selectBackendKind(item.platform_version ?? null);
  return {
    udid: item.udid,
    name: item.name,
    platform_version: item.platform_version,
    state: item.state,
    appium_visible: item.appium_visible,
    backend_kind: normalizedBackendKind,
    ...(item.coredevice_identifier
      ? {coredevice_identifier: item.coredevice_identifier}
      : {}),
  } satisfies DeviceInfo;
}

function hasDeviceUdid(item: DeviceInfo): boolean {
  return Boolean(item.udid);
}

function compareDeviceInfo(left: DeviceInfo, right: DeviceInfo): number {
  return left.name.localeCompare(right.name) || left.udid.localeCompare(right.udid);
}

async function execJson(
  command: string[],
  timeoutMs?: number,
): Promise<Record<string, unknown>> {
  const text = await exec(command, timeoutMs);
  const loaded = JSON.parse(text);
  return typeof loaded === 'object' && loaded
    ? (loaded as Record<string, unknown>)
    : {};
}

async function exec(command: string[], timeoutMs?: number): Promise<string> {
  return await new Promise<string>((resolve, reject) => {
    const spawnOptions = resolveSpawnOptions(command);
    const child = spawn(command[0]!, command.slice(1), {
      stdio: ['ignore', 'pipe', 'pipe'],
      ...spawnOptions,
    });
    let settled = false;
    let timeoutHandle: NodeJS.Timeout | null = null;
    let stdout = '';
    let stderr = '';
    const finalize = (callback: () => void) => {
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
          finalize(() =>
            reject(
              new Error(
                `command timed out after ${timeoutMs}ms: ${command.join(' ')}`,
              ),
            ),
          );
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
        reject(
          new Error(
            `command failed (${code}): ${command.join(' ')}\n${stderr || stdout}`.trim(),
          ),
        );
      });
    });
  });
}

function resolveSpawnOptions(command: string[]): SpawnOptions {
  if (!shouldRunDevicectlAsOriginalUser(command)) {
    return {};
  }
  const uid = Number.parseInt(process.env.SUDO_UID ?? '', 10);
  const gid = Number.parseInt(process.env.SUDO_GID ?? '', 10);
  if (!Number.isFinite(uid) || !Number.isFinite(gid)) {
    return {};
  }
  const env = {...process.env};
  if (process.env.SUDO_USER) {
    env.USER = process.env.SUDO_USER;
    env.LOGNAME = process.env.SUDO_USER;
  }
  return {uid, gid, env};
}

function shouldRunDevicectlAsOriginalUser(command: string[]): boolean {
  return (
    typeof process.getuid === 'function' &&
    process.getuid() === 0 &&
    command[0] === 'xcrun' &&
    command[1] === 'devicectl' &&
    Boolean(process.env.SUDO_UID) &&
    Boolean(process.env.SUDO_GID)
  );
}

function findDeviceEntries(payload: unknown): Record<string, unknown>[] {
  const results: Record<string, unknown>[] = [];
  const stack: unknown[] = [payload];
  while (stack.length > 0) {
    const current = stack.pop();
    if (Array.isArray(current)) {
      stack.push(...current);
      continue;
    }
    if (!current || typeof current !== 'object') {
      continue;
    }
    const mapping = current as Record<string, unknown>;
    if (
      lookup(mapping, 'hardwareProperties.udid', 'udid') &&
      lookup(mapping, 'deviceProperties.name', 'name')
    ) {
      results.push(mapping);
    }
    stack.push(...Object.values(mapping));
  }
  return results;
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

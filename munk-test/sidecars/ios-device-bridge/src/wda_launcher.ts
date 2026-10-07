import {spawn} from 'node:child_process';
import type {SpawnOptions} from 'node:child_process';
import {createRequire} from 'node:module';

import {
  logBridgeEvent,
  normalizeForDiagnostics,
  withBridgeSpan,
} from './diagnostics.js';
import {IOSDeviceBridgeError} from './errors.js';
import {
  DEFAULT_WDA_PORT,
  DEFAULT_WDA_REMOTE_PORT,
  type WdaConnectionInfo,
} from './wda_connection.js';
import {WdaHttpClient} from './wda_http_client.js';
import {createAppiumLogger} from './appium_log.js';
import type {SessionInfo} from './session_types.js';

const APPIUM_PREINSTALLED_MIN_IOS_MAJOR = 17;
const WDA_UI_TESTING_AUTHORIZATION_MAX_ATTEMPTS = 2;
const WDA_UI_TESTING_AUTHORIZATION_RETRY_DELAY_MS = 3000;
const WDA_UI_TESTING_AUTHORIZATION_PATTERNS = [
  'xctdaemonerrordomain code=41',
  'not authorized for performing ui testing actions',
];

const require = createRequire(import.meta.url);
const {WebDriverAgent} = require('appium-webdriveragent') as {
  WebDriverAgent: new (
    args: Record<string, unknown>,
    log?: unknown,
  ) => AppiumWebDriverAgentLike;
};

type AppiumWebDriverAgentLike = {
  launchWithPreinstalledWDA(sessionId: string): Promise<Record<string, unknown> | null>;
  quit(): Promise<void>;
};

type AppiumWdaFactory = (
  info: SessionInfo,
  localPort: number,
) => AppiumWebDriverAgentLike;
type DelayFn = (ms: number) => Promise<void>;

type DevicectlLaunchOptions = {
  env?: Record<string, string | number>;
  terminateExisting?: boolean;
};

const WDA_LAUNCH_TIMEOUT_MS = 60_000;

export interface WdaLauncher {
  launchAndWaitReady(client: WdaHttpClient, connection: WdaConnectionInfo): Promise<void>;
  close(): Promise<void>;
}

export class AppiumPreinstalledWdaLauncher implements WdaLauncher {
  private readonly info: SessionInfo;
  private readonly wdaFactory: AppiumWdaFactory;
  private readonly delayFn: DelayFn;
  private wda: AppiumWebDriverAgentLike | null = null;

  constructor(
    info: SessionInfo,
    wdaFactory: AppiumWdaFactory = createAppiumPreinstalledWda,
    delayFn: DelayFn = delay,
  ) {
    this.info = info;
    this.wdaFactory = wdaFactory;
    this.delayFn = delayFn;
  }

  async launchAndWaitReady(
    client: WdaHttpClient,
    connection: WdaConnectionInfo,
  ): Promise<void> {
    assertPreinstalledSupported(this.info.platformVersion);
    logBridgeEvent(this.info.sessionId, 'bridge.wda.prelaunch-device-interactivity-check', {
      phase: 'wda.launch',
      details: {
        device_udid: this.info.deviceUdid,
        platform_version: this.info.platformVersion,
        note: 'Ensure the device is awake and unlocked before starting WDA.',
      },
    });

    const reachable = await probeWdaStatus(this.info.sessionId, client);
    if (reachable) {
      try {
        await client.ensureReady();
        logBridgeEvent(this.info.sessionId, 'bridge.wda.reuse.success', {
          phase: 'wda.session',
          details: {note: 'Reused an already reachable WDA endpoint.'},
        });
        return;
      } catch (error) {
        logBridgeEvent(this.info.sessionId, 'bridge.wda.reuse.failure', {
          level: 'warn',
          phase: 'wda.session',
          ok: false,
          error,
        });
        await client.close().catch(() => {});
      }
    }

    for (
      let attempt = 1;
      attempt <= WDA_UI_TESTING_AUTHORIZATION_MAX_ATTEMPTS;
      attempt += 1
    ) {
      try {
        await withBridgeSpan(
          this.info.sessionId,
          'bridge.wda.launch',
          'wda.launch',
          {
            launcher: 'appium_preinstalled',
            device_udid: this.info.deviceUdid,
            platform_version: this.info.platformVersion,
            wda_bundle_id: this.info.wdaBundleId,
            wda_port: DEFAULT_WDA_REMOTE_PORT,
            local_forward_port: connection.localPort,
            attempt,
          },
          async () => {
            await launchPreinstalledWda(
              this.info,
              connection,
              client,
              `${this.info.sessionId}-wda-attempt-${attempt}`,
              this.wdaFactory,
              (wda) => {
                this.wda = wda;
              },
            );
          },
        );
        await client.ensureReady();
        return;
      } catch (error) {
        const retryable = isWdaUiTestingAuthorizationError(error);
        if (
          retryable &&
          attempt < WDA_UI_TESTING_AUTHORIZATION_MAX_ATTEMPTS
        ) {
          await client.close().catch(() => {});
          await this.wda?.quit().catch(() => {});
          this.wda = null;
          await this.delayFn(WDA_UI_TESTING_AUTHORIZATION_RETRY_DELAY_MS);
          continue;
        }
        throw toWdaLaunchError(this.info, error, attempt);
      }
    }
  }

  async close(): Promise<void> {
    await this.wda?.quit().catch(() => {});
    this.wda = null;
  }
}

export function createDefaultWdaLauncher(info: SessionInfo): WdaLauncher {
  return new AppiumPreinstalledWdaLauncher(info);
}

function createAppiumPreinstalledWda(
  info: SessionInfo,
  localPort: number,
): AppiumWebDriverAgentLike {
  const {updatedWDABundleId, updatedWDABundleIdSuffix} =
    splitWdaBundleId(info.wdaBundleId);
  return new WebDriverAgent(
    {
      device: {
        udid: info.deviceUdid,
        devicectl: {
          launchApp: async (
            bundleId: string,
            opts: DevicectlLaunchOptions = {},
          ) => {
            await launchWdaRunnerWithOptions(info.deviceUdid, bundleId, opts);
          },
        },
      },
      platformName: 'iOS',
      platformVersion: info.platformVersion,
      realDevice: true,
      wdaLocalPort: localPort,
      wdaRemotePort: DEFAULT_WDA_REMOTE_PORT,
      wdaBaseUrl: 'http://127.0.0.1',
      usePreinstalledWDA: true,
      updatedWDABundleId,
      updatedWDABundleIdSuffix,
    },
    createAppiumLogger(),
  );
}

async function launchPreinstalledWda(
  info: SessionInfo,
  connection: WdaConnectionInfo,
  client: WdaHttpClient,
  wdaSessionId: string,
  wdaFactory: AppiumWdaFactory,
  assignWda: (wda: AppiumWebDriverAgentLike) => void,
): Promise<void> {
  if (connection.localPort === DEFAULT_WDA_PORT) {
    const wda = wdaFactory(info, connection.localPort);
    assignWda(wda);
    await wda.launchWithPreinstalledWDA(wdaSessionId);
    return;
  }
  assignWda(wdaFactory(info, connection.localPort));
  await launchWdaRunnerWithOptions(info.deviceUdid, info.wdaBundleId, {
    terminateExisting: true,
    env: {
      USE_PORT: DEFAULT_WDA_REMOTE_PORT,
      WDA_PRODUCT_BUNDLE_IDENTIFIER: info.wdaBundleId,
    },
  });
  await waitForWdaReachable(client, WDA_LAUNCH_TIMEOUT_MS);
}

async function waitForWdaReachable(
  client: WdaHttpClient,
  timeoutMs: number,
): Promise<void> {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    if (await client.probeStatus()) {
      return;
    }
    await delay(300);
  }
  throw new IOSDeviceBridgeError(
    'wda_launch_failed',
    `Failed to start the preinstalled WebDriverAgent in ${timeoutMs} ms.`,
    502,
  );
}

async function probeWdaStatus(
  sessionId: string,
  client: WdaHttpClient,
): Promise<boolean> {
  const start = Date.now();
  logBridgeEvent(sessionId, 'bridge.wda.status.probe.start', {
    phase: 'wda.status',
    details: {launcher: 'appium_preinstalled'},
  });
  const reachable = await client.probeStatus();
  logBridgeEvent(sessionId, reachable ? 'bridge.wda.status.probe.success' : 'bridge.wda.status.probe.failure', {
    level: reachable ? 'info' : 'warn',
    phase: 'wda.status',
    ok: reachable,
    duration_ms: Date.now() - start,
    details: {reachable},
  });
  return reachable;
}

function assertPreinstalledSupported(platformVersion: string | null): void {
  const major = majorVersionFromString(platformVersion);
  if (major !== null && major >= APPIUM_PREINSTALLED_MIN_IOS_MAJOR) {
    return;
  }
  throw new IOSDeviceBridgeError(
    'wda_unsupported_platform',
    `Preinstalled WDA requires iOS ${APPIUM_PREINSTALLED_MIN_IOS_MAJOR}+ (platform_version=${platformVersion ?? 'unknown'})`,
    400,
    {platform_version: platformVersion},
  );
}

function splitWdaBundleId(wdaBundleId: string): {
  updatedWDABundleId: string;
  updatedWDABundleIdSuffix: string;
} {
  if (wdaBundleId.endsWith('.xctrunner')) {
    return {
      updatedWDABundleId: wdaBundleId.slice(0, -'.xctrunner'.length),
      updatedWDABundleIdSuffix: '.xctrunner',
    };
  }
  return {
    updatedWDABundleId: wdaBundleId,
    updatedWDABundleIdSuffix: '',
  };
}

function isWdaUiTestingAuthorizationError(error: unknown): boolean {
  if (!(error instanceof IOSDeviceBridgeError)) {
    return false;
  }
  if (error.code === 'wda_ui_testing_not_authorized') {
    return true;
  }
  const serialized = JSON.stringify(
    normalizeForDiagnostics({
      message: error.message,
      details: error.details ?? null,
    }),
  ).toLowerCase();
  return WDA_UI_TESTING_AUTHORIZATION_PATTERNS.every((pattern) =>
    serialized.includes(pattern),
  );
}

function toWdaLaunchError(
  info: SessionInfo,
  error: unknown,
  attempt: number,
): IOSDeviceBridgeError {
  if (isWdaUiTestingAuthorizationError(error)) {
    return new IOSDeviceBridgeError(
      'wda_ui_testing_not_authorized',
      'WDA started, but iOS rejected UI testing actions. Wake and unlock the device, then retry. If needed, launch WDA manually once to establish UI testing authorization.',
      502,
      {
        device_udid: info.deviceUdid,
        platform_version: info.platformVersion,
        wda_bundle_id: info.wdaBundleId,
        attempt_count: attempt,
        needs_device_unlock: true,
      },
    );
  }
  if (error instanceof IOSDeviceBridgeError) {
    return new IOSDeviceBridgeError(
      error.code === 'wda_request_failed' ? 'wda_unreachable' : 'wda_launch_failed',
      error.message,
      502,
      {
        device_udid: info.deviceUdid,
        platform_version: info.platformVersion,
        wda_bundle_id: info.wdaBundleId,
        attempt_count: attempt,
        original_error: {code: error.code, message: error.message},
      },
    );
  }
  return new IOSDeviceBridgeError(
    'wda_launch_failed',
    error instanceof Error ? error.message : String(error),
    502,
    {
      device_udid: info.deviceUdid,
      platform_version: info.platformVersion,
      wda_bundle_id: info.wdaBundleId,
      attempt_count: attempt,
    },
  );
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

async function launchWdaRunnerWithOptions(
  deviceUdid: string,
  bundleId: string,
  options: DevicectlLaunchOptions,
): Promise<void> {
  const command = [
    'xcrun',
    'devicectl',
    'device',
    'process',
    'launch',
    '--device',
    deviceUdid,
  ];
  if (options.terminateExisting) {
    command.push('--terminate-existing');
  }
  if (options.env && Object.keys(options.env).length > 0) {
    command.push(
      '--environment-variables',
      JSON.stringify(
        Object.fromEntries(
          Object.entries(options.env).map(([key, value]) => [key, String(value)]),
        ),
      ),
    );
  }
  command.push(bundleId);
  await execUntilStarted(command);
}

async function execUntilStarted(
  command: string[],
  startupWaitMs = 1000,
): Promise<void> {
  return await new Promise<void>((resolve, reject) => {
    const spawnOptions = resolveSpawnOptions(command);
    const child = spawn(command[0]!, command.slice(1), {
      stdio: ['ignore', 'pipe', 'pipe'],
      ...spawnOptions,
    });
    let settled = false;
    let startupTimer: NodeJS.Timeout | null = null;
    let stdout = '';
    let stderr = '';
    const finalize = (callback: () => void) => {
      if (settled) {
        return;
      }
      settled = true;
      if (startupTimer) {
        clearTimeout(startupTimer);
      }
      callback();
    };
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
          resolve();
          return;
        }
        reject(
          new Error(
            `command failed (${code}): ${command.join(' ')}\n${stderr || stdout}`.trim(),
          ),
        );
      });
    });
    startupTimer = setTimeout(() => {
      if (settled) {
        return;
      }
      child.stdout.destroy();
      child.stderr.destroy();
      child.unref();
      finalize(() => resolve());
    }, startupWaitMs);
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

async function delay(ms: number): Promise<void> {
  await new Promise((resolve) => setTimeout(resolve, ms));
}

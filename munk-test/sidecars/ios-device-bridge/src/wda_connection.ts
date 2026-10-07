import {createServer} from 'node:net';

import {DeviceConnectionsFactory} from 'appium-xcuitest-driver/build/lib/device/device-connections-factory.js';
import {checkPortStatus} from 'portscanner';

import {createAppiumLogger} from './appium_log.js';
import {logBridgeEvent, withBridgeSpan} from './diagnostics.js';
import {IOSDeviceBridgeError} from './errors.js';

/** Preferred local listen port (Appium default). */
export const DEFAULT_WDA_PORT = 8100;
/** Device-side WDA HTTP port — always 8100 for preinstalled WDA. */
export const DEFAULT_WDA_REMOTE_PORT = 8100;

const LOCALHOST = '127.0.0.1';
const MAX_DYNAMIC_PORT_ATTEMPTS = 8;

export interface WdaConnectionInfo {
  localPort: number;
  remotePort: number;
  baseUrl: string;
}

export type WdaConnectionFactory = () => DeviceConnectionsFactory;

let sharedFactory: DeviceConnectionsFactory | null = null;

function defaultConnectionFactory(): DeviceConnectionsFactory {
  if (!sharedFactory) {
    sharedFactory = new DeviceConnectionsFactory(
      createAppiumLogger() as unknown as ConstructorParameters<
        typeof DeviceConnectionsFactory
      >[0],
    );
  }
  return sharedFactory;
}

export class WdaConnectionManager {
  private readonly createFactory: WdaConnectionFactory;

  constructor(createFactory: WdaConnectionFactory = defaultConnectionFactory) {
    this.createFactory = createFactory;
  }

  async requestConnection(
    sessionId: string,
    deviceUdid: string,
    platformVersion: string | null,
  ): Promise<WdaConnectionInfo> {
    const factory = this.createFactory();
    await factory.releaseConnection(deviceUdid, DEFAULT_WDA_PORT).catch(() => {});

    const preferredBusy = await isLocalPortOpen(DEFAULT_WDA_PORT);
    const candidates = preferredBusy
      ? await buildDynamicLocalPortCandidates()
      : [DEFAULT_WDA_PORT, ...(await buildDynamicLocalPortCandidates())];

    let lastError: unknown;
    for (const localPort of uniquePorts(candidates)) {
      try {
        const info = await this.requestConnectionOnPort(
          sessionId,
          deviceUdid,
          platformVersion,
          localPort,
          factory,
        );
        return info;
      } catch (error) {
        lastError = error;
        if (!isPortOccupiedError(error)) {
          throw error instanceof IOSDeviceBridgeError
            ? error
            : toConnectionError(deviceUdid, platformVersion, error, localPort);
        }
        await factory.releaseConnection(deviceUdid, localPort).catch(() => {});
      }
    }

    throw toConnectionError(
      deviceUdid,
      platformVersion,
      lastError ??
        new Error(
          `Unable to acquire a free local port for WDA forwarding after ${MAX_DYNAMIC_PORT_ATTEMPTS} attempts`,
        ),
      null,
    );
  }

  async releaseConnection(
    sessionId: string,
    deviceUdid: string,
    localPort: number,
  ): Promise<void> {
    await withBridgeSpan(
      sessionId,
      'bridge.wda.connection.release',
      'wda.connection',
      {device_udid: deviceUdid, local_port: localPort},
      async () => {
        try {
          await this.createFactory().releaseConnection(deviceUdid, localPort);
        } catch (error) {
          throw new IOSDeviceBridgeError(
            'wda_connection_release_failed',
            error instanceof Error ? error.message : String(error),
            502,
            {device_udid: deviceUdid, local_port: localPort},
          );
        }
      },
    );
  }

  private async requestConnectionOnPort(
    sessionId: string,
    deviceUdid: string,
    platformVersion: string | null,
    localPort: number,
    factory: DeviceConnectionsFactory,
  ): Promise<WdaConnectionInfo> {
    await withBridgeSpan(
      sessionId,
      'bridge.wda.connection.request',
      'wda.connection',
      {
        device_udid: deviceUdid,
        platform_version: platformVersion,
        local_port: localPort,
        device_port: DEFAULT_WDA_REMOTE_PORT,
        provider: 'appium-xcuitest-driver',
      },
      async () => {
        await factory.requestConnection(deviceUdid, localPort, {
          usePortForwarding: true,
          devicePort: DEFAULT_WDA_REMOTE_PORT,
          platformVersion,
        });
      },
    );
    const info: WdaConnectionInfo = {
      localPort,
      remotePort: DEFAULT_WDA_REMOTE_PORT,
      baseUrl: `http://${LOCALHOST}:${localPort}`,
    };
    logBridgeEvent(sessionId, 'bridge.wda.connection.ready', {
      phase: 'wda.connection',
      details: {
        base_url: info.baseUrl,
        local_port: info.localPort,
        remote_port: info.remotePort,
        device_udid: deviceUdid,
        platform_version: platformVersion,
        used_default_local_port: localPort === DEFAULT_WDA_PORT,
      },
    });
    return info;
  }
}

async function buildDynamicLocalPortCandidates(): Promise<number[]> {
  const ports: number[] = [];
  for (let attempt = 0; attempt < MAX_DYNAMIC_PORT_ATTEMPTS; attempt += 1) {
    ports.push(await allocateEphemeralPort());
  }
  return ports;
}

async function allocateEphemeralPort(): Promise<number> {
  return await new Promise<number>((resolve, reject) => {
    const server = createServer();
    server.unref();
    server.on('error', reject);
    server.listen(0, LOCALHOST, () => {
      const address = server.address();
      if (address && typeof address === 'object') {
        const port = address.port;
        server.close((error) => {
          if (error) {
            reject(error);
            return;
          }
          resolve(port);
        });
        return;
      }
      reject(new Error('failed to allocate ephemeral WDA local port'));
    });
  });
}

async function isLocalPortOpen(port: number): Promise<boolean> {
  try {
    return (await checkPortStatus(port, LOCALHOST)) === 'open';
  } catch {
    return false;
  }
}

function uniquePorts(ports: number[]): number[] {
  return [...new Set(ports)];
}

function isPortOccupiedError(error: unknown): boolean {
  const message = error instanceof Error ? error.message : String(error);
  const normalized = message.toLowerCase();
  return (
    normalized.includes('is occupied') ||
    normalized.includes('occupied by an other process') ||
    normalized.includes('occupied by another process')
  );
}

function toConnectionError(
  deviceUdid: string,
  platformVersion: string | null,
  error: unknown,
  localPort: number | null,
): IOSDeviceBridgeError {
  const message = error instanceof Error ? error.message : String(error);
  const normalized = message.toLowerCase();
  const needsTunnel =
    normalized.includes('tunnel registry') ||
    normalized.includes('tunnel creation script') ||
    normalized.includes('no tunnel found');
  const portBusy = isPortOccupiedError(error);
  return new IOSDeviceBridgeError(
    needsTunnel ? 'wda_tunnel_unavailable' : 'wda_connection_failed',
    message,
    502,
    {
      device_udid: deviceUdid,
      platform_version: platformVersion,
      local_port: localPort,
      device_port: DEFAULT_WDA_REMOTE_PORT,
      provider: 'appium-xcuitest-driver',
      needs_tunnel_registry: needsTunnel,
      local_port_busy: portBusy,
    },
  );
}

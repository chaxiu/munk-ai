export type DeviceBackendKind = 'appium_ios_device' | 'appium_ios_remotexpc';

export interface CreateSessionRequest {
  device_udid: string;
  bundle_id: string;
  wda_bundle_id?: string;
  platform_version?: string | null;
  diagnostics?: import('./diagnostics.js').DiagnosticsContext | null;
}

export interface DeviceInfo {
  udid: string;
  name: string;
  platform_version: string | null;
  state: string | null;
  appium_visible: boolean;
  backend_kind?: DeviceBackendKind;
  coredevice_identifier?: string | null;
}

export interface SessionInfo {
  sessionId: string;
  deviceUdid: string;
  bundleId: string;
  wdaBundleId: string;
  platformVersion: string | null;
  backendKind: DeviceBackendKind;
}

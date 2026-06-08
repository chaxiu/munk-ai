type DeviceLabelSource = {
  device_ref: string
  display_name?: string | null
}

export function formatDeviceLabel(
  deviceRef: string | null | undefined,
  devices: readonly DeviceLabelSource[],
  fallbackLabel: string
): string {
  if (!deviceRef) {
    return fallbackLabel
  }

  const matched = devices.find((device) => device.device_ref === deviceRef)
  return matched?.display_name?.trim() || deviceRef
}

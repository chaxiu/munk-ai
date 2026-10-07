import { computed, ref, watch } from 'vue'

import { useDevicesQuery } from '@/features/devices/queries/useDevicesQuery'
import { toUserMessage } from '@/features/recording/lib/toUserMessage'

export function useRecordingDeviceSelection() {
  const selectedDeviceRef = ref('')
  const devicesQuery = useDevicesQuery('android')

  const androidDevices = computed(() =>
    (devicesQuery.data.value ?? []).filter((device) => device.platform === 'android')
  )
  const deviceOptions = computed(() =>
    androidDevices.value.map((device) => ({
      label: device.display_name,
      value: device.device_ref,
    }))
  )
  const errorMessage = computed(() => (
    devicesQuery.error.value ? toUserMessage(devicesQuery.error.value) : null
  ))

  watch(androidDevices, (devices) => {
    if (selectedDeviceRef.value && !devices.some((device) => device.device_ref === selectedDeviceRef.value)) {
      selectedDeviceRef.value = ''
    }
  }, { immediate: true })

  return {
    selectedDeviceRef,
    androidDevices,
    deviceOptions,
    devicesLoading: computed(() => devicesQuery.isFetching.value),
    errorMessage,
    refetchDevices: devicesQuery.refetch,
  }
}

import { vi } from 'vitest'

type MockProcedure = (...args: never[]) => unknown

export function typedViFn<T extends MockProcedure = MockProcedure>(implementation?: T) {
  if (implementation) {
    return vi.fn<T>(implementation)
  }
  return vi.fn<T>()
}

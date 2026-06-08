import { beforeEach, describe, expect, it, vi } from 'vitest'

import { logger } from '../logger'

describe('logger', () => {
  beforeEach(() => {
    logger.setLevel('debug')
  })

  it('writes structured error entries to the console sink', () => {
    const spy = vi.spyOn(console, 'error').mockImplementation(() => {})

    logger.error({
      scope: 'test',
      event: 'logger.spec',
      message: 'boom',
      context: {
        route: '/recording',
      },
    })

    expect(spy).toHaveBeenCalledOnce()
    expect(spy.mock.calls[0]?.[1]).toMatchObject({
      scope: 'test',
      event: 'logger.spec',
      message: 'boom',
    })

    spy.mockRestore()
  })
})

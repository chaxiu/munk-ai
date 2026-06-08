import { test } from 'node:test'
import * as assert from 'node:assert'
import { build } from '../helper.js'

test('healthz route returns ok', async (t) => {
  const app = await build(t)

  const res = await app.inject({
    url: '/healthz'
  })
  assert.deepStrictEqual(JSON.parse(res.payload), { status: 'ok' })
})

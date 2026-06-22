import { test } from 'node:test'
import * as assert from 'node:assert'
import { build } from '../helper.js'

test('healthz route returns ok', async (t) => {
  process.env.MUNK_BRIDGE_MANAGER_TOKEN = 'test-token'
  process.env.MUNK_PARENT_PID = '12345'
  t.after(() => {
    delete process.env.MUNK_BRIDGE_MANAGER_TOKEN
    delete process.env.MUNK_PARENT_PID
  })
  const app = await build(t)

  const res = await app.inject({
    url: '/healthz'
  })
  const payload = JSON.parse(res.payload)
  assert.strictEqual(payload.status, 'ok')
  assert.strictEqual(payload.managerToken, 'test-token')
  assert.strictEqual(payload.parentPid, '12345')
  assert.strictEqual(typeof payload.pid, 'number')
  assert.strictEqual(typeof payload.startedAt, 'string')
})

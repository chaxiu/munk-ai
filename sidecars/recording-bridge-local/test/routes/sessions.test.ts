import * as assert from 'node:assert'
import { test } from 'node:test'

import { build } from '../helper.js'
import { readBridgeClientFrame } from '../../src/protocol.js'

test('create and delete bridge session', async (t) => {
  const app = await build(t)

  const createResponse = await app.inject({
    method: 'POST',
    url: '/sessions',
    payload: {
      recording_id: 'rec-1',
      device_ref: 'SER123'
    }
  })

  assert.strictEqual(createResponse.statusCode, 200)
  assert.deepStrictEqual(createResponse.json(), {
    ok: true,
    data: {
      recording_id: 'rec-1',
      device_ref: 'SER123'
    }
  })

  const deleteResponse = await app.inject({
    method: 'DELETE',
    url: '/sessions/rec-1'
  })

  assert.strictEqual(deleteResponse.statusCode, 204)
})

test('readBridgeClientFrame decodes browser text frames carried as Buffer', () => {
  const payload = Buffer.from(JSON.stringify({
    type: 'pointer_down',
    clientCommandId: 'cmd-1',
    pointerId: 0,
    x: 10,
    y: 20,
    width: 100,
    height: 200
  }), 'utf8')

  assert.strictEqual(
    readBridgeClientFrame(payload, false),
    '{"type":"pointer_down","clientCommandId":"cmd-1","pointerId":0,"x":10,"y":20,"width":100,"height":200}'
  )
})

test('readBridgeClientFrame rejects binary websocket frames', () => {
  const payload = Buffer.from([0x01, 0x02, 0x03])

  assert.strictEqual(readBridgeClientFrame(payload, true), null)
})

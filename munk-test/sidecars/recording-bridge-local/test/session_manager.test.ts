import * as assert from 'node:assert'
import { test } from 'node:test'

import { RecordingBridgeSessionManager } from '../src/session_manager.js'

test('dispatchCommand routes commands to the matching session handler', async () => {
  const manager = new RecordingBridgeSessionManager()
  const calls: string[] = []
  const fakeSession = {
    async pointerDown () {
      calls.push('pointer_down')
      return null
    },
    async pointerMove () {
      calls.push('pointer_move')
      return null
    },
    async pointerUp () {
      calls.push('pointer_up')
      return { type: 'forwarding_ack', kind: 'pointer' }
    },
    async input () {
      calls.push('input')
      return { type: 'forwarding_ack', kind: 'input' }
    },
    async back () {
      calls.push('back')
      return { type: 'forwarding_ack', kind: 'back' }
    }
  }

  ;(manager as unknown as { getSession: () => typeof fakeSession }).getSession = () => fakeSession

  await manager.dispatchCommand('rec-1', {
    type: 'pointer_down',
    clientCommandId: 'cmd-1',
    pointerId: 0,
    x: 1,
    y: 2,
    width: 100,
    height: 200
  })
  await manager.dispatchCommand('rec-1', {
    type: 'pointer_move',
    clientCommandId: 'cmd-2',
    pointerId: 0,
    x: 3,
    y: 4,
    width: 100,
    height: 200
  })
  await manager.dispatchCommand('rec-1', {
    type: 'pointer_up',
    clientCommandId: 'cmd-2',
    pointerId: 0,
    x: 5,
    y: 6,
    width: 100,
    height: 200
  })
  await manager.dispatchCommand('rec-1', {
    type: 'input',
    clientCommandId: 'cmd-3',
    text: 'hello'
  })
  await manager.dispatchCommand('rec-1', {
    type: 'back',
    clientCommandId: 'cmd-4'
  })

  assert.deepStrictEqual(calls, ['pointer_down', 'pointer_move', 'pointer_up', 'input', 'back'])
})

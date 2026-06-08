import * as assert from 'node:assert'
import { test } from 'node:test'

import { ScrcpySession } from '../src/scrcpy_session.js'

test('pointer lifecycle injects down/move/up and returns pointer ack on up', async () => {
  const touchCalls: Array<Record<string, unknown>> = []
  const session = new ScrcpySession({ recordingId: 'rec-1' })

  ;(session as unknown as { client: unknown }).client = {
    controller: {
      async injectTouch (message: Record<string, unknown>) {
        touchCalls.push(message)
      }
    }
  }

  await session.pointerDown({
    type: 'pointer_down',
    clientCommandId: 'cmd-pointer',
    pointerId: 0,
    x: 10,
    y: 20,
    width: 100,
    height: 200
  })
  await session.pointerMove({
    type: 'pointer_move',
    clientCommandId: 'cmd-pointer',
    pointerId: 0,
    x: 15,
    y: 30,
    width: 100,
    height: 200
  })
  const ack = await session.pointerUp({
    type: 'pointer_up',
    clientCommandId: 'cmd-pointer',
    pointerId: 0,
    x: 20,
    y: 40,
    width: 100,
    height: 200
  })

  assert.strictEqual(touchCalls.length, 3)
  assert.deepStrictEqual(touchCalls.map((call) => call.action), [0, 2, 1])
  assert.strictEqual(ack.kind, 'pointer')
  assert.deepStrictEqual(ack.payload, {
    pointer_id: 0,
    start_x: 10,
    start_y: 20,
    end_x: 20,
    end_y: 40,
    width: 100,
    height: 200
  })
  assert.deepStrictEqual(ack.steps.map((step) => step.stepKind), ['pointer_down', 'pointer_move', 'pointer_up'])
})

test('pointer move requires an active matching transaction', async () => {
  const session = new ScrcpySession({ recordingId: 'rec-1' })

  ;(session as unknown as { client: unknown }).client = {
    controller: {
      async injectTouch () {}
    }
  }

  await assert.rejects(
    async () => session.pointerMove({
      type: 'pointer_move',
      clientCommandId: 'missing',
      pointerId: 0,
      x: 1,
      y: 2,
      width: 100,
      height: 200
    }),
    /pointer transaction 'missing' was not found/
  )
})

test('back sends key down/up objects instead of positional keycode args', async () => {
  const calls: Array<Record<string, unknown>> = []
  const session = new ScrcpySession({ recordingId: 'rec-1' })

  ;(session as unknown as { client: unknown }).client = {
    controller: {
      async injectKeyCode (message: Record<string, unknown>) {
        calls.push(message)
      }
    }
  }

  await session.back({
    type: 'back',
    clientCommandId: 'cmd-back'
  })

  assert.strictEqual(calls.length, 2)
  assert.deepStrictEqual(calls[0], {
    action: 0,
    keyCode: 4,
    repeat: 0,
    metaState: 0
  })
  assert.deepStrictEqual(calls[1], {
    action: 1,
    keyCode: 4,
    repeat: 0,
    metaState: 0
  })
})

test('input submit sends enter key down/up objects after text injection', async () => {
  const keyCalls: Array<Record<string, unknown>> = []
  const textCalls: string[] = []
  const session = new ScrcpySession({ recordingId: 'rec-1' })

  ;(session as unknown as { client: unknown }).client = {
    controller: {
      async injectText (text: string) {
        textCalls.push(text)
      },
      async injectKeyCode (message: Record<string, unknown>) {
        keyCalls.push(message)
      }
    }
  }

  await session.input({
    type: 'input',
    clientCommandId: 'cmd-input',
    text: 'hello',
    submit: true
  })

  assert.deepStrictEqual(textCalls, ['hello'])
  assert.deepStrictEqual(keyCalls, [
    {
      action: 0,
      keyCode: 66,
      repeat: 0,
      metaState: 0
    },
    {
      action: 1,
      keyCode: 66,
      repeat: 0,
      metaState: 0
    }
  ])
})

import * as assert from 'node:assert'
import { test } from 'node:test'

import { parseBridgeClientCommand } from '../src/protocol.js'

test('parseBridgeClientCommand parses pointer down command', () => {
  const command = parseBridgeClientCommand(JSON.stringify({
    type: 'pointer_down',
    clientCommandId: 'cmd-1',
    pointerId: 0,
    x: 12,
    y: 34,
    width: 1080,
    height: 2400
  }))

  assert.deepStrictEqual(command, {
    type: 'pointer_down',
    clientCommandId: 'cmd-1',
    pointerId: 0,
    x: 12,
    y: 34,
    width: 1080,
    height: 2400
  })
})

test('parseBridgeClientCommand parses pointer move and up commands', () => {
  const move = parseBridgeClientCommand(JSON.stringify({
    type: 'pointer_move',
    clientCommandId: 'cmd-2',
    pointerId: 0,
    x: 100,
    y: 200,
    width: 1080,
    height: 2400
  }))
  const up = parseBridgeClientCommand(JSON.stringify({
    type: 'pointer_up',
    clientCommandId: 'cmd-2',
    pointerId: 0,
    x: 300,
    y: 400,
    width: 1080,
    height: 2400
  }))

  assert.equal(move.type, 'pointer_move')
  assert.equal(up.type, 'pointer_up')
  if (move.type !== 'pointer_move' || up.type !== 'pointer_up') {
    throw new Error('expected pointer move/up commands')
  }
  assert.equal(move.pointerId, 0)
  assert.equal(up.x, 300)
})

test('parseBridgeClientCommand parses input and back commands', () => {
  const input = parseBridgeClientCommand(JSON.stringify({
    type: 'input',
    clientCommandId: 'cmd-3',
    text: 'hello',
    submit: true
  }))
  const back = parseBridgeClientCommand(JSON.stringify({
    type: 'back',
    clientCommandId: 'cmd-4'
  }))

  assert.deepStrictEqual(input, {
    type: 'input',
    clientCommandId: 'cmd-3',
    text: 'hello',
    submit: true
  })
  assert.deepStrictEqual(back, {
    type: 'back',
    clientCommandId: 'cmd-4'
  })
})

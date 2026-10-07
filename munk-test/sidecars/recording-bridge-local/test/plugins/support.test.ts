import { test } from 'node:test'
import * as assert from 'node:assert'
import Fastify from 'fastify'
import Support from '../../src/plugins/support.js'

test('support works standalone', async (t) => {
  const fastify = Fastify()
  // eslint-disable-next-line no-void
  void fastify.register(Support)
  await fastify.ready()

  assert.equal(fastify.someSupport(), 'hugs')
})

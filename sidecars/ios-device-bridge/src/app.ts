import * as path from 'node:path';

import AutoLoad, { type AutoloadPluginOptions } from '@fastify/autoload';
import cors from '@fastify/cors';
import sensible from '@fastify/sensible';
import { type FastifyPluginAsync } from 'fastify';
import { fileURLToPath } from 'node:url';

import { IOSDeviceBridgeSessionManager } from './session_manager.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

export type AppOptions = {} & Partial<AutoloadPluginOptions>;

const options: AppOptions = {};

const app: FastifyPluginAsync<AppOptions> = async (
  fastify,
  opts,
): Promise<void> => {
  const sessionManager = new IOSDeviceBridgeSessionManager();
  fastify.decorate('iosDeviceBridgeSessionManager', sessionManager);
  void fastify.register(cors, {origin: true});
  void fastify.register(sensible);
  fastify.addHook('onClose', async () => {
    await sessionManager.closeAll();
  });
  void fastify.register(AutoLoad, {
    dir: path.join(__dirname, 'routes'),
    options: opts,
    forceESM: true,
  });
};

export default app;
export {app, options};

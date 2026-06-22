import {type FastifyPluginAsync, type FastifyReply} from 'fastify';

import {IOSDeviceBridgeError} from '../errors.js';
import {
  type IOSDeviceBridgeSessionManager,
  listRealDevices,
  type CreateSessionRequest,
} from '../session_manager.js';

const BRIDGE_STARTED_AT = new Date().toISOString();

const bridgeRoutes: FastifyPluginAsync = async (fastify): Promise<void> => {
  const manager = fastify as typeof fastify & {
    iosDeviceBridgeSessionManager: IOSDeviceBridgeSessionManager;
  };

  fastify.get('/healthz', async function () {
    return {
      status: 'ok',
      managerToken: process.env.MUNK_BRIDGE_MANAGER_TOKEN ?? null,
      parentPid: process.env.MUNK_PARENT_PID ?? null,
      pid: process.pid,
      startedAt: BRIDGE_STARTED_AT,
    };
  });

  fastify.get('/devices', async function () {
    return {ok: true, data: await listRealDevices()};
  });

  fastify.post<{Body: CreateSessionRequest}>(
    '/sessions',
    async function (request, reply) {
      try {
        const session =
          await manager.iosDeviceBridgeSessionManager.createSession(
            request.body,
          );
        return {ok: true, data: session};
      } catch (error) {
        return sendBridgeError(reply, error);
      }
    },
  );

  fastify.get<{Params: {sessionId: string}}>(
    '/sessions/:sessionId',
    async function (request, reply) {
      try {
        const session = manager.iosDeviceBridgeSessionManager.getSessionInfo(
          request.params.sessionId,
        );
        return {ok: true, data: session};
      } catch (error) {
        return sendBridgeError(reply, error);
      }
    },
  );

  fastify.get<{Params: {sessionId: string}}>(
    '/sessions/:sessionId/diagnostics',
    async function (request, reply) {
      try {
        return {
          ok: true,
          data: manager.iosDeviceBridgeSessionManager.getSessionDiagnostics(
            request.params.sessionId,
          ),
        };
      } catch (error) {
        return sendBridgeError(reply, error);
      }
    },
  );

  fastify.delete<{Params: {sessionId: string}}>(
    '/sessions/:sessionId',
    async function (request, reply) {
      await manager.iosDeviceBridgeSessionManager.deleteSession(
        request.params.sessionId,
      );
      return reply.code(204).send();
    },
  );

  fastify.post<{Params: {sessionId: string}}>(
    '/sessions/:sessionId/wda/ensure-ready',
    async function (request, reply) {
      try {
        const session = await manager.iosDeviceBridgeSessionManager.ensureWdaReady(
          request.params.sessionId,
        );
        return {ok: true, data: session};
      } catch (error) {
        return sendBridgeError(reply, error);
      }
    },
  );

  fastify.post<{Params: {sessionId: string}}>(
    '/sessions/:sessionId/device/screenshot',
    async function (request, reply) {
      try {
        const pngBase64 =
          await manager.iosDeviceBridgeSessionManager.screenshotPngBase64(
            request.params.sessionId,
          );
        return {ok: true, data: {png_base64: pngBase64}};
      } catch (error) {
        return sendBridgeError(reply, error);
      }
    },
  );

  fastify.post<{Params: {sessionId: string}; Body: {x: number; y: number}}>(
    '/sessions/:sessionId/device/tap',
    async function (request, reply) {
      try {
        await manager.iosDeviceBridgeSessionManager.tap(
          request.params.sessionId,
          request.body.x,
          request.body.y,
        );
        return {ok: true};
      } catch (error) {
        return sendBridgeError(reply, error);
      }
    },
  );

  fastify.post<{
    Params: {sessionId: string};
    Body: {x: number; y: number; duration_sec?: number | null};
  }>('/sessions/:sessionId/device/long-press', async function (request, reply) {
    try {
      await manager.iosDeviceBridgeSessionManager.longPress(
        request.params.sessionId,
        request.body.x,
        request.body.y,
        request.body.duration_sec ?? null,
      );
      return {ok: true};
    } catch (error) {
      return sendBridgeError(reply, error);
    }
  });

  fastify.post<{
    Params: {sessionId: string};
    Body: {
      start_x: number;
      start_y: number;
      end_x: number;
      end_y: number;
      duration_sec?: number | null;
    };
  }>('/sessions/:sessionId/device/swipe', async function (request, reply) {
    try {
      await manager.iosDeviceBridgeSessionManager.swipe(
        request.params.sessionId,
        {
          startX: request.body.start_x,
          startY: request.body.start_y,
          endX: request.body.end_x,
          endY: request.body.end_y,
          durationSec: request.body.duration_sec ?? null,
        },
      );
      return {ok: true};
    } catch (error) {
      return sendBridgeError(reply, error);
    }
  });

  fastify.post<{Params: {sessionId: string}; Body: {text: string}}>(
    '/sessions/:sessionId/device/type-text',
    async function (request, reply) {
      try {
        await manager.iosDeviceBridgeSessionManager.typeText(
          request.params.sessionId,
          request.body.text,
        );
        return {ok: true};
      } catch (error) {
        return sendBridgeError(reply, error);
      }
    },
  );

  fastify.post<{Params: {sessionId: string}}>(
    '/sessions/:sessionId/device/clear-text',
    async function (request, reply) {
      try {
        await manager.iosDeviceBridgeSessionManager.clearText(
          request.params.sessionId,
        );
        return {ok: true};
      } catch (error) {
        return sendBridgeError(reply, error);
      }
    },
  );

  fastify.post<{Params: {sessionId: string}; Body: {key: string}}>(
    '/sessions/:sessionId/device/press',
    async function (request, reply) {
      try {
        await manager.iosDeviceBridgeSessionManager.press(
          request.params.sessionId,
          request.body.key,
        );
        return {ok: true};
      } catch (error) {
        return sendBridgeError(reply, error);
      }
    },
  );

  fastify.post<{Params: {sessionId: string}}>(
    '/sessions/:sessionId/device/dismiss-soft-keyboard',
    async function (request, reply) {
      try {
        await manager.iosDeviceBridgeSessionManager.dismissSoftKeyboard(
          request.params.sessionId,
        );
        return {ok: true};
      } catch (error) {
        return sendBridgeError(reply, error);
      }
    },
  );

  fastify.get<{Params: {sessionId: string}}>(
    '/sessions/:sessionId/device/window-size',
    async function (request, reply) {
      try {
        return {
          ok: true,
          data: await manager.iosDeviceBridgeSessionManager.windowSize(
            request.params.sessionId,
          ),
        };
      } catch (error) {
        return sendBridgeError(reply, error);
      }
    },
  );

  fastify.get<{Params: {sessionId: string}}>(
    '/sessions/:sessionId/device/current-app',
    async function (request, reply) {
      try {
        return {
          ok: true,
          data: await manager.iosDeviceBridgeSessionManager.currentApp(
            request.params.sessionId,
          ),
        };
      } catch (error) {
        return sendBridgeError(reply, error);
      }
    },
  );

  fastify.get<{Params: {sessionId: string}}>(
    '/sessions/:sessionId/device/accessibility-tree',
    async function (request, reply) {
      try {
        return {
          ok: true,
          data: await manager.iosDeviceBridgeSessionManager.accessibilityTree(
            request.params.sessionId,
          ),
        };
      } catch (error) {
        return sendBridgeError(reply, error);
      }
    },
  );

  fastify.post<{Params: {sessionId: string}; Body: {bundle_id: string}}>(
    '/sessions/:sessionId/apps/launch',
    async function (request, reply) {
      try {
        await manager.iosDeviceBridgeSessionManager.launchApp(
          request.params.sessionId,
          request.body.bundle_id,
        );
        return {ok: true};
      } catch (error) {
        return sendBridgeError(reply, error);
      }
    },
  );

  fastify.post<{Params: {sessionId: string}; Body: {bundle_id: string}}>(
    '/sessions/:sessionId/apps/terminate',
    async function (request, reply) {
      try {
        await manager.iosDeviceBridgeSessionManager.terminateApp(
          request.params.sessionId,
          request.body.bundle_id,
        );
        return {ok: true};
      } catch (error) {
        return sendBridgeError(reply, error);
      }
    },
  );
};

function sendBridgeError(reply: FastifyReply, error: unknown) {
  if (error instanceof IOSDeviceBridgeError) {
    return reply.code(error.statusCode).send({
      ok: false,
      error: {
        code: error.code,
        message: error.message,
        details: error.details ?? null,
      },
    });
  }
  return reply.code(500).send({
    ok: false,
    error: {
      code: 'bridge_internal_error',
      message: error instanceof Error ? error.message : String(error),
    },
  });
}

export default bridgeRoutes;

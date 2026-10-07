import { MutationCache, QueryCache, QueryClient } from '@tanstack/vue-query'

import { logger } from '@/shared/logging/logger'
import { DEFAULT_QUERY_GC_TIME_MS, DEFAULT_QUERY_STALE_TIME_MS } from './defaults'
import { getQueryErrorMessage } from './errors'

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: DEFAULT_QUERY_STALE_TIME_MS,
      gcTime: DEFAULT_QUERY_GC_TIME_MS,
      refetchOnWindowFocus: false,
    },
    mutations: {
      retry: 0,
    },
  },
  queryCache: new QueryCache({
    onError: (error, query) => {
      logger.error({
        scope: 'query',
        event: 'query.error',
        message: getQueryErrorMessage(error),
        context: {
          queryKey: query.queryKey,
        },
      })
    },
  }),
  mutationCache: new MutationCache({
    onError: (error, _variables, _context, mutation) => {
      logger.error({
        scope: 'mutation',
        event: 'mutation.error',
        message: getQueryErrorMessage(error),
        context: {
          mutationKey: mutation.options.mutationKey,
        },
      })
    },
  }),
})

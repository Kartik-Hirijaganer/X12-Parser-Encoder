import { useEffect, useState } from 'react'

interface UseApiState<T> {
  data: T | null
  error: Error | null
  loading: boolean
  reload: () => Promise<void>
}

export function useApi<T>(
  requestFactory: (() => Promise<T>) | null,
  deps: ReadonlyArray<unknown> = [],
): UseApiState<T> {
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState<Error | null>(null)
  const [loading, setLoading] = useState<boolean>(Boolean(requestFactory))
  const [reloadToken, setReloadToken] = useState(0)

  const depsKey = JSON.stringify(deps)

  useEffect(() => {
    let cancelled = false

    async function runRequest() {
      if (!requestFactory) {
        setLoading(false)
        return
      }

      setLoading(true)
      setError(null)

      try {
        const nextData = await requestFactory()
        if (!cancelled) {
          setData(nextData)
        }
      } catch (caughtError) {
        if (!cancelled) {
          setError(caughtError instanceof Error ? caughtError : new Error('Unknown request error'))
        }
      } finally {
        if (!cancelled) {
          setLoading(false)
        }
      }
    }

    void runRequest()

    return () => {
      cancelled = true
    }
  }, [depsKey, reloadToken, requestFactory])

  return {
    data,
    error,
    loading,
    reload: async () => {
      setReloadToken((value) => value + 1)
    },
  }
}

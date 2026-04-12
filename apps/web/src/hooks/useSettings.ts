import { useEffect, useState } from 'react'

import type { SubmitterConfig } from '../types/settings'
import { DEFAULT_SUBMITTER_CONFIG, SETTINGS_STORAGE_KEY } from '../utils/constants'

function readStoredSettings(): SubmitterConfig {
  if (typeof window === 'undefined') {
    return DEFAULT_SUBMITTER_CONFIG
  }

  const rawValue = window.localStorage.getItem(SETTINGS_STORAGE_KEY)
  if (!rawValue) {
    return DEFAULT_SUBMITTER_CONFIG
  }

  try {
    const parsedValue = JSON.parse(rawValue) as Partial<SubmitterConfig>
    return { ...DEFAULT_SUBMITTER_CONFIG, ...parsedValue }
  } catch {
    return DEFAULT_SUBMITTER_CONFIG
  }
}

export function useSettings() {
  const [settings] = useState<SubmitterConfig>(() => readStoredSettings())

  useEffect(() => {
    window.localStorage.setItem(SETTINGS_STORAGE_KEY, JSON.stringify(settings))
  }, [settings])

  return settings
}

import { useEffect, useLayoutEffect, useRef } from 'react'

export interface ShortcutBinding {
  keys: string | readonly string[]
  handler: (event: KeyboardEvent) => void
  enabled?: boolean
  allowInInput?: boolean
}

const SEQUENCE_WINDOW_MS = 1000

function isEditableElement(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) {
    return false
  }
  if (target.isContentEditable) {
    return true
  }
  const tag = target.tagName
  return tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT'
}

function normalizeKey(event: KeyboardEvent): string {
  if (event.key === ' ') {
    return 'Space'
  }
  return event.key.length === 1 ? event.key.toLowerCase() : event.key
}

export function useKeyboardShortcut(bindings: readonly ShortcutBinding[]): void {
  const bindingsRef = useRef(bindings)

  useLayoutEffect(() => {
    bindingsRef.current = bindings
  }, [bindings])

  useEffect(() => {
    if (typeof window === 'undefined') {
      return
    }

    let bufferKeys: string[] = []
    let bufferExpiresAt = 0

    function handleKeyDown(event: KeyboardEvent) {
      if (event.defaultPrevented) {
        return
      }

      const activeBindings = bindingsRef.current
      const pressedKey = normalizeKey(event)
      const now = Date.now()

      if (now > bufferExpiresAt) {
        bufferKeys = []
      }

      bufferKeys = [...bufferKeys, pressedKey].slice(-4)
      bufferExpiresAt = now + SEQUENCE_WINDOW_MS

      for (const binding of activeBindings) {
        if (binding.enabled === false) {
          continue
        }
        if (!binding.allowInInput && isEditableElement(event.target)) {
          continue
        }

        const sequence = Array.isArray(binding.keys) ? binding.keys : [binding.keys as string]
        if (sequence.length === 0) {
          continue
        }
        if (bufferKeys.length < sequence.length) {
          continue
        }

        const tail = bufferKeys.slice(-sequence.length)
        const match = sequence.every((key, index) => key === tail[index])

        if (match) {
          binding.handler(event)
          bufferKeys = []
          bufferExpiresAt = 0
          return
        }
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [])
}

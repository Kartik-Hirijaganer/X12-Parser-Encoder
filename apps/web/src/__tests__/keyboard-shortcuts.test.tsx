import { act, fireEvent, renderHook } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { useKeyboardShortcut } from '../hooks/useKeyboardShortcut'

describe('useKeyboardShortcut', () => {
  it('fires a single-key binding', () => {
    const handler = vi.fn()
    renderHook(() => useKeyboardShortcut([{ keys: '?', handler }]))

    act(() => {
      fireEvent.keyDown(window, { key: '?' })
    })

    expect(handler).toHaveBeenCalledTimes(1)
  })

  it('fires a sequence binding only after both keys are pressed', () => {
    const handler = vi.fn()
    renderHook(() => useKeyboardShortcut([{ keys: ['g', 'd'], handler }]))

    act(() => {
      fireEvent.keyDown(window, { key: 'g' })
    })
    expect(handler).not.toHaveBeenCalled()

    act(() => {
      fireEvent.keyDown(window, { key: 'd' })
    })
    expect(handler).toHaveBeenCalledTimes(1)
  })

  it('does not fire when focus is in an editable element', () => {
    const handler = vi.fn()
    renderHook(() => useKeyboardShortcut([{ keys: '?', handler }]))

    const input = document.createElement('input')
    document.body.appendChild(input)
    input.focus()

    act(() => {
      fireEvent.keyDown(input, { key: '?' })
    })

    expect(handler).not.toHaveBeenCalled()
    document.body.removeChild(input)
  })

  it('ignores a binding when enabled is false', () => {
    const handler = vi.fn()
    renderHook(() => useKeyboardShortcut([{ keys: '?', handler, enabled: false }]))

    act(() => {
      fireEvent.keyDown(window, { key: '?' })
    })

    expect(handler).not.toHaveBeenCalled()
  })
})

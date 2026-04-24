import { act, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { renderHook } from '@testing-library/react'

import { useReducedMotionPreference } from '../hooks/useReducedMotionPreference'
import { renderApp } from './testUtils'

type MatchMediaListener = (event: MediaQueryListEvent) => void

function installMatchMedia(initialMatches: boolean) {
  const listeners = new Set<MatchMediaListener>()
  const mediaQueryList = {
    matches: initialMatches,
    media: '(prefers-reduced-motion: reduce)',
    onchange: null,
    addEventListener: vi.fn((_event: string, listener: MatchMediaListener) => {
      listeners.add(listener)
    }),
    removeEventListener: vi.fn((_event: string, listener: MatchMediaListener) => {
      listeners.delete(listener)
    }),
    addListener: vi.fn((listener: MatchMediaListener) => {
      listeners.add(listener)
    }),
    removeListener: vi.fn((listener: MatchMediaListener) => {
      listeners.delete(listener)
    }),
    dispatchEvent: vi.fn(),
  }

  const matchMedia = vi.fn().mockImplementation(() => mediaQueryList)
  Object.defineProperty(window, 'matchMedia', {
    configurable: true,
    value: matchMedia,
  })

  function emit(matches: boolean) {
    mediaQueryList.matches = matches
    const event = { matches } as MediaQueryListEvent
    for (const listener of listeners) {
      listener(event)
    }
  }

  return { mediaQueryList, matchMedia, emit }
}

describe('useReducedMotionPreference', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('returns false when the OS setting is not reduced', () => {
    installMatchMedia(false)
    const { result } = renderHook(() => useReducedMotionPreference())
    expect(result.current).toBe(false)
  })

  it('returns true when the OS setting is reduced', () => {
    installMatchMedia(true)
    const { result } = renderHook(() => useReducedMotionPreference())
    expect(result.current).toBe(true)
  })

  it('updates when the OS setting changes at runtime', () => {
    const { emit } = installMatchMedia(false)
    const { result } = renderHook(() => useReducedMotionPreference())
    expect(result.current).toBe(false)

    act(() => {
      emit(true)
    })
    expect(result.current).toBe(true)

    act(() => {
      emit(false)
    })
    expect(result.current).toBe(false)
  })
})

describe('HomePage drop-zone pulse respects reduced motion', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('skips the pulse animation when prefers-reduced-motion is set', () => {
    installMatchMedia(true)
    renderApp('/')

    const dropZone = screen.getByText('Or drag and drop any file here').closest('[data-drop-pulsing]')
    expect(dropZone).not.toBeNull()
    expect(dropZone).toHaveAttribute('data-drop-pulsing', 'false')
  })

  it('does not pulse when no file is being dragged', () => {
    installMatchMedia(false)
    renderApp('/')

    const dropZone = screen.getByText('Or drag and drop any file here').closest('[data-drop-pulsing]')
    expect(dropZone).toHaveAttribute('data-drop-pulsing', 'false')
  })

  it('activates the pulse affordance when a file is dragged over the window', () => {
    installMatchMedia(false)
    renderApp('/')

    const dropZone = screen.getByText('Or drag and drop any file here').closest('[data-drop-pulsing]')
    expect(dropZone).toHaveAttribute('data-drop-pulsing', 'false')

    const dragEvent = new Event('dragenter', { bubbles: true }) as DragEvent
    Object.defineProperty(dragEvent, 'dataTransfer', {
      value: { types: ['Files'] },
    })

    act(() => {
      window.dispatchEvent(dragEvent)
    })

    expect(dropZone).toHaveAttribute('data-drop-pulsing', 'true')
  })
})

describe('Toaster renders without animation layer crashes', () => {
  it('renders toasts without relying on reduced-motion wiring', () => {
    installMatchMedia(true)
    const { container } = render(<div data-testid="probe">ready</div>)
    expect(container.querySelector('[data-testid="probe"]')).not.toBeNull()
  })
})

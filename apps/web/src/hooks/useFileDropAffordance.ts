import { useEffect, useState } from 'react'

export function useFileDropAffordance(): boolean {
  const [isDraggingWindow, setIsDraggingWindow] = useState(false)

  useEffect(() => {
    if (typeof window === 'undefined') {
      return
    }

    let dragDepth = 0

    function hasFileDrag(event: DragEvent): boolean {
      const types = event.dataTransfer?.types
      if (!types) {
        return false
      }
      for (let index = 0; index < types.length; index += 1) {
        if (types[index] === 'Files' || types[index] === 'application/x-moz-file') {
          return true
        }
      }
      return false
    }

    function handleDragEnter(event: DragEvent) {
      if (!hasFileDrag(event)) {
        return
      }
      dragDepth += 1
      setIsDraggingWindow(true)
    }

    function handleDragLeave(event: DragEvent) {
      if (!hasFileDrag(event)) {
        return
      }
      dragDepth = Math.max(0, dragDepth - 1)
      if (dragDepth === 0) {
        setIsDraggingWindow(false)
      }
    }

    function handleDrop() {
      dragDepth = 0
      setIsDraggingWindow(false)
    }

    window.addEventListener('dragenter', handleDragEnter)
    window.addEventListener('dragleave', handleDragLeave)
    window.addEventListener('drop', handleDrop)
    window.addEventListener('dragend', handleDrop)

    return () => {
      window.removeEventListener('dragenter', handleDragEnter)
      window.removeEventListener('dragleave', handleDragLeave)
      window.removeEventListener('drop', handleDrop)
      window.removeEventListener('dragend', handleDrop)
    }
  }, [])

  return isDraggingWindow
}

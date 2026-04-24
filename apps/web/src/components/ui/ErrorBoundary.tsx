import { Component, type ErrorInfo, type ReactNode } from 'react'

import { Button } from './Button'
import { EmptyState } from './EmptyState'
import { WarningIcon } from './Icons'

interface ErrorBoundaryProps {
  children: ReactNode
  fallback?: (reset: () => void) => ReactNode
  onError?: (error: Error, info: ErrorInfo) => void
}

interface ErrorBoundaryState {
  hasError: boolean
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = { hasError: false }

  static getDerivedStateFromError(): ErrorBoundaryState {
    return { hasError: true }
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    this.props.onError?.(error, info)
  }

  reset = () => {
    this.setState({ hasError: false })
  }

  render() {
    if (!this.state.hasError) {
      return this.props.children
    }

    if (this.props.fallback) {
      return this.props.fallback(this.reset)
    }

    return (
      <div className="mx-auto max-w-xl p-6">
        <EmptyState
          action={
            <Button
              onClick={() => {
                this.reset()
                if (typeof window !== 'undefined') {
                  window.location.reload()
                }
              }}
              variant="primary"
            >
              Reload page
            </Button>
          }
          description="An unexpected error interrupted this view. Reload to try again, or go back to the previous page."
          icon={<WarningIcon className="h-10 w-10" />}
          title="Something went wrong"
        />
      </div>
    )
  }
}

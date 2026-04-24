import { lazy, Suspense, type ReactElement } from 'react'
import { BrowserRouter, Route, Routes, useLocation } from 'react-router-dom'

import { KeyboardShortcuts } from './components/KeyboardShortcuts'
import { RouteTransition } from './components/transitions/RouteTransition'
import { ErrorBoundary } from './components/ui/ErrorBoundary'
import { Toaster } from './components/ui/Toast'
import { SettingsProvider } from './hooks/useSettings'
import { EligibilityDashboardPage } from './pages/EligibilityDashboardPage'
import { GenerateResultPage } from './pages/GenerateResultPage'
import { HomePage } from './pages/HomePage'
import { PreviewPage } from './pages/PreviewPage'
import { SettingsPage } from './pages/SettingsPage'
import { TemplatesPage } from './pages/TemplatesPage'
import { ValidationResultPage } from './pages/ValidationResultPage'

const UiGalleryPage = lazy(() =>
  import('./pages/UiGalleryPage').then((module) => ({ default: module.UiGalleryPage })),
)

function routeElement(node: ReactElement) {
  return <ErrorBoundary>{node}</ErrorBoundary>
}

export function AppRoutes() {
  const location = useLocation()
  return (
    <Routes location={location}>
      <Route element={routeElement(<HomePage />)} path="/" />
      <Route element={routeElement(<PreviewPage />)} path="/preview" />
      <Route element={routeElement(<GenerateResultPage />)} path="/generate/result" />
      <Route element={routeElement(<ValidationResultPage />)} path="/validate/result" />
      <Route element={routeElement(<EligibilityDashboardPage />)} path="/dashboard" />
      <Route element={routeElement(<TemplatesPage />)} path="/templates" />
      <Route element={routeElement(<SettingsPage />)} path="/settings" />
      {import.meta.env.DEV ? (
        <Route
          element={routeElement(
            <Suspense fallback={null}>
              <UiGalleryPage />
            </Suspense>,
          )}
          path="/__ui"
        />
      ) : null}
      <Route element={routeElement(<HomePage />)} path="*" />
    </Routes>
  )
}

function App() {
  return (
    <ErrorBoundary>
      <SettingsProvider>
        <BrowserRouter>
          <KeyboardShortcuts />
          <RouteTransition>
            <AppRoutes />
          </RouteTransition>
          <Toaster />
        </BrowserRouter>
      </SettingsProvider>
    </ErrorBoundary>
  )
}

export default App

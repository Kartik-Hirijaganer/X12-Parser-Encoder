import { BrowserRouter, Route, Routes } from 'react-router-dom'

import { SettingsProvider } from './hooks/useSettings'
import { EligibilityDashboardPage } from './pages/EligibilityDashboardPage'
import { GenerateResultPage } from './pages/GenerateResultPage'
import { HomePage } from './pages/HomePage'
import { PreviewPage } from './pages/PreviewPage'
import { SettingsPage } from './pages/SettingsPage'
import { TemplatesPage } from './pages/TemplatesPage'
import { ValidationResultPage } from './pages/ValidationResultPage'

export function AppRoutes() {
  return (
    <Routes>
      <Route element={<HomePage />} path="/" />
      <Route element={<PreviewPage />} path="/preview" />
      <Route element={<GenerateResultPage />} path="/generate/result" />
      <Route element={<ValidationResultPage />} path="/validate/result" />
      <Route element={<EligibilityDashboardPage />} path="/dashboard" />
      <Route element={<TemplatesPage />} path="/templates" />
      <Route element={<SettingsPage />} path="/settings" />
      <Route element={<HomePage />} path="*" />
    </Routes>
  )
}

function App() {
  return (
    <SettingsProvider>
      <BrowserRouter>
        <AppRoutes />
      </BrowserRouter>
    </SettingsProvider>
  )
}

export default App

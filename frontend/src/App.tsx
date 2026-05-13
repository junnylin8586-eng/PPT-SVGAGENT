import { Routes, Route } from 'react-router-dom'
import Header from '@/components/layout/Header'
import HomePage from '@/pages/HomePage'
import WorkspacePage from '@/pages/WorkspacePage'
import TemplateGalleryPage from '@/pages/TemplateGalleryPage'

export default function App() {
  return (
    <div style={{ minHeight: '100vh', background: 'var(--color-bg-subtle)' }}>
      <Header />
      <main>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/workspace/:projectId" element={<WorkspacePage />} />
          <Route path="/templates" element={<TemplateGalleryPage />} />
          <Route path="/history" element={<HomePage />} />
        </Routes>
      </main>
    </div>
  )
}

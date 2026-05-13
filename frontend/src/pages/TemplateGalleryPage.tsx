import { useEffect, useState } from 'react'
import { api } from '@/api/client'
import { Layout, Check } from 'lucide-react'

interface LayoutTemplate {
  layout_id: string
  name: string
  category: string
  thumbnail?: string
  slide_width?: number
  slide_height?: number
}

export default function TemplateGalleryPage() {
  const [layouts, setLayouts] = useState<LayoutTemplate[]>([])
  const [loading, setLoading] = useState(true)
  const [selected, setSelected] = useState<string | null>(null)

  useEffect(() => {
    api.getLayouts().then(r => {
      setLayouts(r.data?.templates || r.data || [])
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [])

  // Group by category (backend already returns Chinese categories)
  const categories = [...new Set(layouts.map(l => l.category))]

  return (
    <div className="gallery-page">
      <div className="gallery-header">
        <h1>模板库</h1>
        <p>选择布局模板，应用于您的 PPT 项目</p>
      </div>

      {loading ? (
        <div className="loading-center">
          <div className="spinner" />
        </div>
      ) : (
        <>
          {categories.map(cat => (
            <div key={cat} className="category-section">
              <h2 className="category-title">{cat}</h2>
              <div className="template-grid">
                {layouts.filter(l => l.category === cat).map(layout => (
                  <div
                    key={layout.layout_id}
                    className={`template-card card ${selected === layout.layout_id ? 'selected' : ''}`}
                    onClick={() => setSelected(layout.layout_id)}
                  >
                    <div className="template-thumb">
                      <Layout size={32} color="var(--color-primary)" opacity={0.5} />
                    </div>
                    <div className="template-info">
                      <span className="template-name">{layout.name}</span>
                      {selected === layout.layout_id && (
                        <span className="selected-badge">
                          <Check size={12} /> 已选择
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </>
      )}

      <style>{`
        .gallery-page {
          max-width: 1200px;
          margin: 0 auto;
          padding: 32px 24px;
        }
        .gallery-header { margin-bottom: 32px; }
        .gallery-header h1 { font-size: 22px; font-weight: 700; color: var(--color-text); margin-bottom: 4px; }
        .gallery-header p { font-size: 14px; color: var(--color-text-muted); }
        .loading-center { display: flex; justify-content: center; padding: 80px; }
        .spinner { width: 36px; height: 36px; border: 3px solid var(--color-border); border-top-color: var(--color-primary); border-radius: 50%; animation: spin 0.8s linear infinite; }
        @keyframes spin { to { transform: rotate(360deg); } }
        .category-section { margin-bottom: 32px; }
        .category-title { font-size: 15px; font-weight: 600; color: var(--color-text); margin-bottom: 14px; padding-left: 4px; }
        .template-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 14px; }
        .template-card { padding: 0; overflow: hidden; cursor: pointer; transition: all 0.2s; border: 2px solid transparent; }
        .template-card:hover { transform: translateY(-2px); box-shadow: var(--shadow-lg); }
        .template-card.selected { border-color: var(--color-primary); }
        .template-thumb { width: 100%; aspect-ratio: 16/9; background: var(--color-bg-subtle); display: flex; align-items: center; justify-content: center; }
        .template-info { padding: 12px 14px; display: flex; align-items: center; justify-content: space-between; }
        .template-name { font-size: 13px; font-weight: 500; color: var(--color-text); }
        .selected-badge { display: flex; align-items: center; gap: 4px; font-size: 11px; color: var(--color-primary); font-weight: 600; }
      `}</style>
    </div>
  )
}

/**
 * TemplateSelectorModal - 模板选择器（带缩略图）
 */
import { useState, useEffect } from 'react'
import { X, Layout, Check, Search } from 'lucide-react'
import { api, type LayoutTemplate } from '@/api/client'

interface Props {
  open: boolean
  selected: string
  onSelect: (templateId: string) => void
  onClose: () => void
}

const CATEGORY_LABELS: Record<string, string> = {
  '政府央企': '政府央企',
  '学术教育': '学术教育',
  '金融银行': '金融银行',
  '医疗健康': '医疗健康',
  '科技AI': '科技AI',
  '通用商务': '通用商务',
}

export default function TemplateSelectorModal({ open, selected, onSelect, onClose }: Props) {
  const [templates, setTemplates] = useState<LayoutTemplate[]>([])
  const [loading, setLoading] = useState(false)
  const [search, setSearch] = useState('')
  const [activeCategory, setActiveCategory] = useState('全部')

  useEffect(() => {
    if (!open) return
    setLoading(true)
    api.getLayouts().then(r => {
      setTemplates(r.data?.templates || [])
    }).finally(() => setLoading(false))
  }, [open])

  if (!open) return null

  const categories = ['全部', ...Object.values(CATEGORY_LABELS).filter(Boolean)]
  const filtered = templates.filter(t => {
    const matchSearch = !search ||
      t.name.includes(search) ||
      t.summary?.includes(search) ||
      (t.keywords || []).some((k: string) => k.toLowerCase().includes(search.toLowerCase()))
    const matchCat = activeCategory === '全部' ||
      t.category === activeCategory ||
      (activeCategory === '通用商务' && !['政府央企', '学术教育', '金融银行', '医疗健康', '科技AI'].includes(t.category))
    return matchSearch && matchCat
  })

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-box wide" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h2>选择模板</h2>
          <button className="modal-close" onClick={onClose}><X size={20} /></button>
        </div>

        <div className="modal-toolbar">
          <div className="search-box">
            <Search size={15} color="#999" />
            <input
              type="text"
              placeholder="搜索模板名称、场景..."
              value={search}
              onChange={e => setSearch(e.target.value)}
            />
          </div>
          <div className="category-tabs">
            {categories.map(cat => (
              <button
                key={cat}
                className={`cat-tab ${activeCategory === cat ? 'active' : ''}`}
                onClick={() => setActiveCategory(cat)}
              >
                {cat}
              </button>
            ))}
          </div>
        </div>

        <div className="modal-body">
          {loading ? (
            <div className="loading-grid">
              {Array.from({ length: 8 }).map((_, i) => (
                <div key={i} className="skeleton-card" />
              ))}
            </div>
          ) : (
            <div className="template-grid">
              {filtered.map(t => (
                <div
                  key={t.layout_id}
                  className={`tmpl-card ${selected === t.layout_id ? 'selected' : ''}`}
                  onClick={() => { onSelect(t.layout_id); onClose() }}
                >
                  {/* 缩略图 */}
                  <div className="tmpl-thumb">
                    <img
                      src={`/template_thumbs/${t.layout_id}.png`}
                      alt={t.name}
                      className="tmpl-thumb-img"
                      onError={e => { (e.target as HTMLImageElement).style.display = 'none' }}
                    />
                    {selected === t.layout_id && (
                      <div className="tmpl-selected-badge">
                        <Check size={14} color="white" />
                      </div>
                    )}
                  </div>
                  <div className="tmpl-info">
                    <span className="tmpl-name">{t.name}</span>
                    <span className="tmpl-cat">{t.category}</span>
                    <span className="tmpl-desc">{t.summary?.slice(0, 40) || ''}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      <style>{`
        .modal-overlay {
          position: fixed; inset: 0;
          background: rgba(0,0,0,0.45);
          display: flex; align-items: center; justify-content: center;
          z-index: 1000; backdrop-filter: blur(2px);
        }
        .modal-box { background: white; border-radius: 12px; width: 860px; max-width: 95vw; box-shadow: 0 20px 60px rgba(0,0,0,0.2); overflow: hidden; }
        .modal-box.wide { width: 860px; }
        .modal-header { display: flex; align-items: center; justify-content: space-between; padding: 18px 24px; border-bottom: 1px solid var(--color-border); }
        .modal-header h2 { font-size: 16px; font-weight: 600; color: var(--color-text); }
        .modal-close { width: 32px; height: 32px; border-radius: 6px; border: none; background: var(--color-bg-subtle); color: var(--color-text-muted); cursor: pointer; display: flex; align-items: center; justify-content: center; }
        .modal-close:hover { background: var(--color-border); }
        .modal-toolbar { padding: 14px 24px; border-bottom: 1px solid var(--color-border); display: flex; flex-direction: column; gap: 10px; }
        .search-box { display: flex; align-items: center; gap: 8px; padding: 8px 14px; border: 1.5px solid var(--color-border); border-radius: 8px; }
        .search-box input { border: none; outline: none; font-size: 14px; flex: 1; font-family: inherit; }
        .category-tabs { display: flex; gap: 6px; flex-wrap: wrap; }
        .cat-tab { padding: 5px 14px; border-radius: 20px; border: 1px solid var(--color-border); background: white; font-size: 13px; color: var(--color-text-muted); cursor: pointer; transition: all 0.2s; }
        .cat-tab:hover { border-color: var(--color-primary); color: var(--color-primary); }
        .cat-tab.active { background: var(--color-primary); color: white; border-color: var(--color-primary); }
        .modal-body { padding: 20px 24px; max-height: 65vh; overflow-y: auto; }
        .loading-grid, .template-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 14px; }
        .skeleton-card { height: 180px; border-radius: 8px; background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%); background-size: 200% 100%; animation: shimmer 1.5s infinite; }
        @keyframes shimmer { 0% { background-position: 200% 0; } 100% { background-position: -200% 0; } }
        .tmpl-card { border: 2px solid var(--color-border); border-radius: 8px; overflow: hidden; cursor: pointer; transition: all 0.2s; background: white; }
        .tmpl-card:hover { border-color: var(--color-primary-light); transform: translateY(-2px); box-shadow: var(--shadow-md); }
        .tmpl-card.selected { border-color: var(--color-primary); }
        .tmpl-thumb { width: 100%; aspect-ratio: 16/9; background: var(--color-bg-subtle); display: flex; align-items: center; justify-content: center; position: relative; overflow: hidden; }
        .tmpl-thumb-img { width: 100%; height: 100%; object-fit: cover; display: block; }
        .tmpl-selected-badge { position: absolute; top: 8px; right: 8px; width: 24px; height: 24px; background: var(--color-primary); border-radius: 50%; display: flex; align-items: center; justify-content: center; }
        .tmpl-info { padding: 12px; display: flex; flex-direction: column; gap: 2px; }
        .tmpl-name { font-size: 13px; font-weight: 600; color: var(--color-text); }
        .tmpl-cat { font-size: 11px; color: var(--color-primary); font-weight: 500; }
        .tmpl-desc { font-size: 11px; color: var(--color-text-muted); line-height: 1.4; margin-top: 4px; overflow: hidden; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; }
      `}</style>
    </div>
  )
}
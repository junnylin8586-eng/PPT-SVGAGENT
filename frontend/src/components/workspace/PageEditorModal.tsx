/**
 * PageEditorModal - 编辑单页大纲/描述
 */
import { useState } from 'react'
import { X, Check, Trash2 } from 'lucide-react'
import { api } from '@/api/client'
import type { Page } from '@/api/client'

interface Props {
  open: boolean
  page: Page | null
  pageIndex: number
  projectId: string
  onClose: () => void
  onSaved: () => void
}

export default function PageEditorModal({ open, page, pageIndex, projectId, onClose, onSaved }: Props) {
  const [outline, setOutline] = useState(page?.outline_content || '')
  const [part, setPart] = useState(page?.part || '')
  const [description, setDescription] = useState(page?.description_content || '')
  const [saving, setSaving] = useState(false)
  const [activeTab, setActiveTab] = useState<'outline' | 'description'>('outline')

  if (!open || !page) return null

  const handleSave = async () => {
    setSaving(true)
    try {
      await api.updatePage(projectId, page.page_id, {
        outline_content: outline,
        part,
        description_content: description,
      })
      onSaved()
      onClose()
    } catch (e) {
      console.error(e)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-box" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h2>编辑第 {pageIndex + 1} 页</h2>
          <button className="modal-close" onClick={onClose}><X size={18} /></button>
        </div>

        <div className="tab-bar">
          <button className={`tab ${activeTab === 'outline' ? 'active' : ''}`} onClick={() => setActiveTab('outline')}>大纲内容</button>
          <button className={`tab ${activeTab === 'description' ? 'active' : ''}`} onClick={() => setActiveTab('description')}>详细描述</button>
        </div>

        <div className="modal-body">
          <div className="form-group">
            <label>页面标题（章节名）</label>
            <input
              type="text"
              className="form-input"
              placeholder="例如：项目背景"
              value={part}
              onChange={e => setPart(e.target.value)}
            />
          </div>

          {activeTab === 'outline' && (
            <div className="form-group">
              <label>本页大纲（AI 生成依据）</label>
              <textarea
                className="form-textarea"
                placeholder="描述这一页要呈现的内容要点，AI 将根据此内容生成幻灯片..."
                value={outline}
                onChange={e => setOutline(e.target.value)}
                rows={5}
              />
              <p className="field-hint">AI 会根据此处内容生成对应的幻灯片 SVG，建议简洁明确。</p>
            </div>
          )}

          {activeTab === 'description' && (
            <div className="form-group">
              <label>详细描述（可选，辅助 AI 更好地理解内容）</label>
              <textarea
                className="form-textarea"
                placeholder="补充更详细的内容描述、数据、案例等，帮助 AI 生成更精准的页面..."
                value={description}
                onChange={e => setDescription(e.target.value)}
                rows={6}
              />
            </div>
          )}
        </div>

        <div className="modal-footer">
          <button className="btn btn-secondary" onClick={onClose}>取消</button>
          <button className="btn btn-primary" onClick={handleSave} disabled={saving}>
            <Check size={14} /> {saving ? '保存中...' : '保存'}
          </button>
        </div>
      </div>

      <style>{`
        .modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.45); display: flex; align-items: center; justify-content: center; z-index: 1000; backdrop-filter: blur(2px); }
        .modal-box { background: white; border-radius: 12px; width: 560px; max-width: 95vw; box-shadow: 0 20px 60px rgba(0,0,0,0.2); overflow: hidden; }
        .modal-header { display: flex; align-items: center; justify-content: space-between; padding: 18px 24px; border-bottom: 1px solid var(--color-border); }
        .modal-header h2 { font-size: 16px; font-weight: 600; color: var(--color-text); }
        .modal-close { width: 30px; height: 30px; border-radius: 6px; border: none; background: var(--color-bg-subtle); color: var(--color-text-muted); cursor: pointer; display: flex; align-items: center; justify-content: center; }
        .tab-bar { display: flex; border-bottom: 1px solid var(--color-border); padding: 0 24px; background: var(--color-bg-subtle); }
        .tab { padding: 10px 16px; border: none; background: none; font-size: 13px; font-weight: 500; color: var(--color-text-muted); cursor: pointer; border-bottom: 2px solid transparent; margin-bottom: -1px; }
        .tab.active { color: var(--color-primary); border-bottom-color: var(--color-primary); }
        .modal-body { padding: 20px 24px; display: flex; flex-direction: column; gap: 16px; }
        .form-group { display: flex; flex-direction: column; gap: 6px; }
        .form-group label { font-size: 13px; font-weight: 600; color: var(--color-text); }
        .form-input, .form-textarea { padding: 10px 14px; border: 1.5px solid var(--color-border); border-radius: 8px; font-size: 14px; font-family: inherit; outline: none; transition: border-color 0.2s; resize: vertical; }
        .form-input:focus, .form-textarea:focus { border-color: var(--color-primary); }
        .form-textarea { min-height: 120px; }
        .field-hint { font-size: 12px; color: var(--color-text-muted); }
        .modal-footer { display: flex; justify-content: flex-end; gap: 10px; padding: 14px 24px; border-top: 1px solid var(--color-border); background: var(--color-bg-subtle); }
        .btn { display: inline-flex; align-items: center; gap: 6px; padding: 8px 18px; border-radius: 6px; font-size: 14px; font-weight: 500; cursor: pointer; border: none; transition: all 0.2s; }
        .btn-secondary { background: white; color: var(--color-text); border: 1px solid var(--color-border); }
        .btn-secondary:hover { background: var(--color-bg-subtle); }
        .btn-primary { background: var(--color-primary); color: white; }
        .btn-primary:hover { background: var(--color-primary-light); }
        .btn-primary:disabled { opacity: 0.6; cursor: not-allowed; }
      `}</style>
    </div>
  )
}
/**
 * OutlineEditorModal - 编辑项目整体大纲（页面列表增删排序）
 */
import { useState } from 'react'
import { X, Plus, Trash2, GripVertical, Check } from 'lucide-react'
import { api } from '@/api/client'

interface OutlineItem {
  tempId: string  // 临时 ID（新增但未保存的页面）
  page_id?: string  // 已有页面 ID
  order_index: number
  part: string
  outline_content: string
}

interface Props {
  open: boolean
  projectId: string
  initialPages: { page_id: string; order_index: number; part: string; outline_content: string }[]
  onClose: () => void
  onSaved: (newPageIds: string[]) => void  // 返回新增/更新的页面 ID
}

let tempCounter = 0

export default function OutlineEditorModal({ open, projectId, initialPages, onClose, onSaved }: Props) {
  const [items, setItems] = useState<OutlineItem[]>(() =>
    initialPages.map(p => ({ ...p, tempId: `new_${p.page_id || ++tempCounter}` }))
  )
  const [saving, setSaving] = useState(false)
  const [dragIdx, setDragIdx] = useState<number | null>(null)

  if (!open) return null

  const updateItem = (idx: number, field: keyof OutlineItem, value: string) => {
    setItems(prev => prev.map((it, i) => i === idx ? { ...it, [field]: value } : it))
  }

  const addItem = () => {
    setItems(prev => [
      ...prev,
      { tempId: `new_${++tempCounter}`, order_index: prev.length, part: '', outline_content: '' }
    ])
  }

  const removeItem = (idx: number) => {
    if (items.length <= 1) return  // 至少保留一页
    setItems(prev => prev.filter((_, i) => i !== idx).map((it, i) => ({ ...it, order_index: i })))
  }

  const moveItem = (from: number, to: number) => {
    if (to < 0 || to >= items.length) return
    const arr = [...items]
    const [moved] = arr.splice(from, 1)
    arr.splice(to, 0, moved)
    setItems(arr.map((it, i) => ({ ...it, order_index: i })))
  }

  const handleSave = async () => {
    setSaving(true)
    try {
      // 过滤出有内容的页面
      const validItems = items.filter(it => it.outline_content.trim() || it.part.trim())
      if (validItems.length === 0) { onClose(); return }

      const outlines = validItems.map((it, idx) => ({
        order_index: idx,
        part: it.part.trim(),
        outline_content: it.outline_content.trim(),
      }))

      await api.createPages(projectId, outlines)
      onSaved([])
      onClose()
    } catch (e) {
      console.error(e)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-box outline-modal" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h2>编辑大纲</h2>
          <button className="modal-close" onClick={onClose}><X size={18} /></button>
        </div>

        <div className="modal-hint">
          调整页面顺序、修改标题和大纲内容，AI 将根据最终结果重新生成所有页面。
        </div>

        <div className="modal-body outline-body">
          {items.map((item, idx) => (
            <div key={item.tempId} className={`outline-item ${dragIdx === idx ? 'dragging' : ''}`}>
              <div className="drag-handle" onMouseDown={() => setDragIdx(idx)}>
                <GripVertical size={16} color="#999" />
              </div>
              <div className="outline-item-content">
                <div className="item-row">
                  <input
                    type="text"
                    className="form-input part-input"
                    placeholder="页面标题（章节名）"
                    value={item.part}
                    onChange={e => updateItem(idx, 'part', e.target.value)}
                  />
                  <div className="page-num-badge">{idx + 1}</div>
                  <button
                    className="remove-btn"
                    onClick={() => removeItem(idx)}
                    disabled={items.length <= 1}
                    title="删除此页"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
                <textarea
                  className="form-textarea outline-textarea"
                  placeholder="本页大纲内容，描述要呈现的核心要点..."
                  value={item.outline_content}
                  onChange={e => updateItem(idx, 'outline_content', e.target.value)}
                  rows={2}
                />
                <div className="move-btns">
                  <button className="move-btn" onClick={() => moveItem(idx, idx - 1)} disabled={idx === 0}>↑ 上移</button>
                  <button className="move-btn" onClick={() => moveItem(idx, idx + 1)} disabled={idx === items.length - 1}>下移 ↓</button>
                </div>
              </div>
            </div>
          ))}
        </div>

        <div className="modal-footer">
          <button className="btn btn-secondary" onClick={addItem}>
            <Plus size={14} /> 添加页面
          </button>
          <div style={{ flex: 1 }} />
          <button className="btn btn-secondary" onClick={onClose}>取消</button>
          <button className="btn btn-primary" onClick={handleSave} disabled={saving}>
            <Check size={14} /> {saving ? '保存中...' : '保存大纲'}
          </button>
        </div>
      </div>

      <style>{`
        .modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.45); display: flex; align-items: flex-start; justify-content: center; z-index: 1000; backdrop-filter: blur(2px); padding-top: 5vh; overflow-y: auto; }
        .outline-modal { background: white; border-radius: 12px; width: 640px; max-width: 95vw; box-shadow: 0 20px 60px rgba(0,0,0,0.2); overflow: hidden; margin-bottom: 5vh; }
        .modal-header { display: flex; align-items: center; justify-content: space-between; padding: 18px 24px; border-bottom: 1px solid var(--color-border); }
        .modal-header h2 { font-size: 16px; font-weight: 600; color: var(--color-text); }
        .modal-close { width: 30px; height: 30px; border-radius: 6px; border: none; background: var(--color-bg-subtle); color: var(--color-text-muted); cursor: pointer; display: flex; align-items: center; justify-content: center; }
        .modal-hint { font-size: 13px; color: var(--color-text-muted); padding: 12px 24px; background: #EBF5FF; border-bottom: 1px solid #BFDBFE; }
        .outline-body { padding: 16px 24px; max-height: 55vh; overflow-y: auto; display: flex; flex-direction: column; gap: 12px; }
        .outline-item { display: flex; gap: 10px; padding: 14px; border: 1.5px solid var(--color-border); border-radius: 8px; background: white; transition: all 0.15s; }
        .outline-item.dragging { opacity: 0.5; border-color: var(--color-primary); }
        .drag-handle { padding-top: 4px; cursor: grab; flex-shrink: 0; }
        .outline-item-content { flex: 1; display: flex; flex-direction: column; gap: 8px; }
        .item-row { display: flex; align-items: center; gap: 8px; }
        .part-input { flex: 1; padding: 7px 12px; border: 1.5px solid var(--color-border); border-radius: 6px; font-size: 13px; font-weight: 600; font-family: inherit; outline: none; }
        .part-input:focus { border-color: var(--color-primary); }
        .page-num-badge { font-size: 12px; font-weight: 700; color: var(--color-primary); background: #EBF5FF; padding: 3px 10px; border-radius: 12px; flex-shrink: 0; }
        .remove-btn { width: 28px; height: 28px; border-radius: 6px; border: none; background: transparent; color: var(--color-text-light); cursor: pointer; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
        .remove-btn:hover:not(:disabled) { background: #FEE2E2; color: #DC2626; }
        .remove-btn:disabled { opacity: 0.3; cursor: default; }
        .outline-textarea { min-height: 60px; padding: 8px 12px; border: 1.5px solid var(--color-border); border-radius: 6px; font-size: 13px; font-family: inherit; outline: none; resize: vertical; }
        .outline-textarea:focus { border-color: var(--color-primary); }
        .move-btns { display: flex; gap: 8px; }
        .move-btn { padding: 3px 10px; border-radius: 4px; border: 1px solid var(--color-border); background: white; font-size: 11px; color: var(--color-text-muted); cursor: pointer; }
        .move-btn:hover:not(:disabled) { border-color: var(--color-primary); color: var(--color-primary); }
        .move-btn:disabled { opacity: 0.4; cursor: default; }
        .modal-footer { display: flex; align-items: center; gap: 10px; padding: 14px 24px; border-top: 1px solid var(--color-border); background: var(--color-bg-subtle); }
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
/**
 * StyleSettingsModal - 样式自定义（配色/字体/布局/主题预设）
 */
import { useState } from 'react'
import { X, Check, Palette } from 'lucide-react'
import { api } from '@/api/client'

interface StyleSettings {
  primary_color: string
  font_family: string
  layout_style: string
}

interface Props {
  open: boolean
  projectId: string
  initial: StyleSettings
  onClose: () => void
  onSaved: () => void
}

const PRESET_THEMES = [
  { name: '政府蓝', color: '#003371', font: 'system-ui', desc: '稳重权威、政务汇报' },
  { name: '科技蓝', color: '#0066FF', font: 'Inter', desc: '现代科技、AI 主题' },
  { name: '商务黑', color: '#1A1A2E', font: 'system-ui', desc: '高端商务、董事会' },
  { name: '清新绿', color: '#059669', font: 'system-ui', desc: '绿色环保、可持续发展' },
  { name: '活力橙', color: '#E07B39', font: 'system-ui', desc: '营销推广、活动策划' },
  { name: '学术紫', color: '#7C3AED', font: 'Georgia', desc: '学术演讲、研究汇报' },
]

const COLOR_OPTIONS = [
  '#003371', '#0066FF', '#1A1A2E', '#059669', '#E07B39', '#7C3AED',
  '#0891B2', '#DC2626', '#92400E', '#1D4ED8', '#065F46', '#831843',
]

const FONT_OPTIONS = [
  { label: '系统默认 (system-ui)', value: 'system-ui' },
  { label: '思源黑体 (Noto Sans SC)', value: '"Noto Sans SC"' },
  { label: '微软雅黑', value: '"Microsoft YaHei"' },
  { label: '苹方', value: '"PingFang SC"' },
  { label: 'Georgia (英文)', value: 'Georgia' },
  { label: 'Inter (英文)', value: 'Inter' },
]

const LAYOUT_OPTIONS = [
  { value: 'compact', label: '紧凑', desc: '信息密度高，适合数据汇报' },
  { value: 'balanced', label: '均衡', desc: '留白适中，适合商务演示（推荐）' },
  { value: 'spacious', label: '舒展', desc: '大量留白，适合演讲展示' },
]

export default function StyleSettingsModal({ open, projectId, initial, onClose, onSaved }: Props) {
  const [primaryColor, setPrimaryColor] = useState(initial.primary_color || '#003371')
  const [fontFamily, setFontFamily] = useState(initial.font_family || 'system-ui')
  const [layoutStyle, setLayoutStyle] = useState(initial.layout_style || 'balanced')
  const [customColor, setCustomColor] = useState(initial.primary_color || '#003371')
  const [saving, setSaving] = useState(false)
  const [tab, setTab] = useState<'themes' | 'custom'>('themes')

  if (!open) return null

  const handleSave = async () => {
    setSaving(true)
    try {
      await api.updateProject(projectId, {
        primary_color: primaryColor,
        font_family: fontFamily,
        layout_style: layoutStyle,
      } as any)
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
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <Palette size={18} color="var(--color-primary)" />
            <h2>样式设置</h2>
          </div>
          <button className="modal-close" onClick={onClose}><X size={18} /></button>
        </div>

        <div className="tab-bar">
          <button className={`tab ${tab === 'themes' ? 'active' : ''}`} onClick={() => setTab('themes')}>主题预设</button>
          <button className={`tab ${tab === 'custom' ? 'active' : ''}`} onClick={() => setTab('custom')}>自定义</button>
        </div>

        <div className="modal-body">
          {tab === 'themes' && (
            <div className="theme-grid">
              {PRESET_THEMES.map(t => (
                <div
                  key={t.name}
                  className={`theme-card ${primaryColor === t.color ? 'selected' : ''}`}
                  onClick={() => { setPrimaryColor(t.color); setFontFamily(t.font) }}
                >
                  <div className="theme-swatch" style={{ background: t.color }} />
                  <div className="theme-info">
                    <span className="theme-name">{t.name}</span>
                    <span className="theme-desc">{t.desc}</span>
                  </div>
                  {primaryColor === t.color && (
                    <div className="theme-check"><Check size={12} color="white" /></div>
                  )}
                </div>
              ))}
            </div>
          )}

          {tab === 'custom' && (
            <div className="custom-panel">
              {/* 配色 */}
              <div className="custom-section">
                <label className="custom-label">主色调</label>
                <div className="color-row">
                  {COLOR_OPTIONS.map(c => (
                    <button
                      key={c}
                      className={`color-swatch ${primaryColor === c ? 'selected' : ''}`}
                      style={{ background: c }}
                      onClick={() => setPrimaryColor(c)}
                    />
                  ))}
                </div>
                <div className="custom-input-row">
                  <input
                    type="color"
                    value={customColor}
                    onChange={e => { setPrimaryColor(e.target.value); setCustomColor(e.target.value) }}
                    className="color-picker"
                  />
                  <input
                    type="text"
                    className="hex-input"
                    value={primaryColor}
                    onChange={e => setPrimaryColor(e.target.value)}
                    placeholder="#003371"
                  />
                  <span className="hex-label">十六进制颜色值</span>
                </div>
                {/* 预览 */}
                <div className="color-preview" style={{ background: primaryColor }}>
                  <span style={{ color: 'white', fontSize: 13, fontWeight: 600 }}>Aa 示例文字</span>
                  <span style={{ color: 'rgba(255,255,255,0.75)', fontSize: 11 }}>Preview Text</span>
                </div>
              </div>

              {/* 字体 */}
              <div className="custom-section">
                <label className="custom-label">字体</label>
                <div className="font-list">
                  {FONT_OPTIONS.map(f => (
                    <label key={f.value} className={`font-item ${fontFamily === f.value ? 'selected' : ''}`}>
                      <input
                        type="radio"
                        name="font"
                        value={f.value}
                        checked={fontFamily === f.value}
                        onChange={() => setFontFamily(f.value)}
                        style={{ display: 'none' }}
                      />
                      <span className="font-label" style={{ fontFamily: f.value }}>{f.label}</span>
                      {fontFamily === f.value && <Check size={13} color="var(--color-primary)" />}
                    </label>
                  ))}
                </div>
              </div>

              {/* 布局 */}
              <div className="custom-section">
                <label className="custom-label">布局密度</label>
                <div className="layout-options">
                  {LAYOUT_OPTIONS.map(opt => (
                    <label key={opt.value} className={`layout-item ${layoutStyle === opt.value ? 'selected' : ''}`}>
                      <input
                        type="radio"
                        name="layout"
                        value={opt.value}
                        checked={layoutStyle === opt.value}
                        onChange={() => setLayoutStyle(opt.value)}
                        style={{ display: 'none' }}
                      />
                      <span className="layout-label">{opt.label}</span>
                      <span className="layout-desc">{opt.desc}</span>
                      {layoutStyle === opt.value && <Check size={13} color="var(--color-primary)" />}
                    </label>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>

        <div className="modal-footer">
          <button className="btn btn-secondary" onClick={onClose}>取消</button>
          <button className="btn btn-primary" onClick={handleSave} disabled={saving}>
            {saving ? '保存中...' : '保存样式'}
          </button>
        </div>
      </div>

      <style>{`
        .tab-bar { display: flex; border-bottom: 1px solid var(--color-border); padding: 0 24px; background: var(--color-bg-subtle); }
        .tab { padding: 10px 16px; border: none; background: none; font-size: 13px; font-weight: 500; color: var(--color-text-muted); cursor: pointer; border-bottom: 2px solid transparent; margin-bottom: -1px; }
        .tab.active { color: var(--color-primary); border-bottom-color: var(--color-primary); }
        .theme-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; }
        .theme-card { display: flex; align-items: center; gap: 12px; padding: 12px 14px; border: 2px solid var(--color-border); border-radius: 8px; cursor: pointer; transition: all 0.2s; position: relative; }
        .theme-card:hover { border-color: var(--color-primary-light); transform: translateY(-1px); }
        .theme-card.selected { border-color: var(--color-primary); background: #EBF5FF; }
        .theme-swatch { width: 40px; height: 40px; border-radius: 8px; flex-shrink: 0; }
        .theme-info { flex: 1; display: flex; flex-direction: column; gap: 2px; }
        .theme-name { font-size: 13px; font-weight: 600; color: var(--color-text); }
        .theme-desc { font-size: 11px; color: var(--color-text-muted); }
        .theme-check { position: absolute; top: 6px; right: 6px; width: 20px; height: 20px; background: var(--color-primary); border-radius: 50%; display: flex; align-items: center; justify-content: center; }
        .custom-panel { display: flex; flex-direction: column; gap: 20px; }
        .custom-section { display: flex; flex-direction: column; gap: 10px; }
        .custom-label { font-size: 13px; font-weight: 600; color: var(--color-text); }
        .color-row { display: flex; flex-wrap: wrap; gap: 8px; }
        .color-swatch { width: 28px; height: 28px; border-radius: 6px; border: 2px solid transparent; cursor: pointer; transition: transform 0.15s; }
        .color-swatch:hover { transform: scale(1.15); }
        .color-swatch.selected { border-color: white; box-shadow: 0 0 0 2px var(--color-primary); }
        .custom-input-row { display: flex; align-items: center; gap: 10px; }
        .color-picker { width: 40px; height: 36px; border: 1px solid var(--color-border); border-radius: 6px; cursor: pointer; padding: 2px; }
        .hex-input { padding: 7px 12px; border: 1.5px solid var(--color-border); border-radius: 6px; font-size: 13px; font-family: monospace; width: 110px; outline: none; }
        .hex-input:focus { border-color: var(--color-primary); }
        .hex-label { font-size: 12px; color: var(--color-text-muted); }
        .color-preview { margin-top: 8px; border-radius: 8px; padding: 14px 18px; display: flex; flex-direction: column; gap: 4px; }
        .font-list { display: flex; flex-direction: column; gap: 4px; }
        .font-item { display: flex; align-items: center; justify-content: space-between; padding: 9px 14px; border-radius: 6px; border: 1.5px solid var(--color-border); cursor: pointer; transition: all 0.15s; }
        .font-item:hover { border-color: var(--color-primary-light); }
        .font-item.selected { border-color: var(--color-primary); background: #EBF5FF; }
        .font-label { font-size: 13px; color: var(--color-text); }
        .layout-options { display: flex; flex-direction: column; gap: 6px; }
        .layout-item { display: flex; align-items: center; gap: 10px; padding: 10px 14px; border-radius: 6px; border: 1.5px solid var(--color-border); cursor: pointer; transition: all 0.15s; }
        .layout-item:hover { border-color: var(--color-primary-light); }
        .layout-item.selected { border-color: var(--color-primary); background: #EBF5FF; }
        .layout-label { font-size: 13px; font-weight: 600; color: var(--color-text); width: 48px; }
        .layout-desc { font-size: 12px; color: var(--color-text-muted); flex: 1; }

      `}</style>
    </div>
  )
}
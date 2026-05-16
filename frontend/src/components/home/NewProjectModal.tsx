/**
 * NewProjectModal - 新建项目一步到位
 * Step 1: 基本信息（名称 + 主题描述）
 * Step 2: 选择模板（带缩略图）
 * Step 3: 选择样式（主题预设）
 * 自动生成 → 跳转工作区
 */
import { useState, useEffect } from 'react'
import { X, Sparkles, ArrowRight, ArrowLeft, Check, Loader, Layout, Plus } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { api, type LayoutTemplate, type ThemeOutline } from '@/api/client'

interface Props {
  onClose: () => void
}

const QUICK_STYLES = [
  { name: '政府蓝', color: '#003371', font: 'system-ui' },
  { name: '科技蓝', color: '#0066FF', font: 'Inter' },
  { name: '商务黑', color: '#1A1A2E', font: 'system-ui' },
  { name: '清新绿', color: '#059669', font: 'system-ui' },
  { name: '活力橙', color: '#E07B39', font: 'system-ui' },
  { name: '学术紫', color: '#7C3AED', font: 'Georgia' },
]

const DEFAULT_OUTLINES = [
  { order_index: 0, outline_content: '项目背景与目标', part: '概述' },
  { order_index: 1, outline_content: '现状分析', part: '分析' },
  { order_index: 2, outline_content: '实施路径与方法', part: '方法' },
  { order_index: 3, outline_content: '成果展示', part: '成果' },
  { order_index: 4, outline_content: '总结与展望', part: '总结' },
]

export default function NewProjectModal({ onClose }: Props) {
  const navigate = useNavigate()
  const [step, setStep] = useState<1 | 2 | 3>(1)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  // Step 1 fields
  const [name, setName] = useState('')
  const [theme, setTheme] = useState('')

  // Step 1b: AI outline analysis
  const [analyzing, setAnalyzing] = useState(false)
  const [analysisError, setAnalysisError] = useState('')
  const [aiOutlines, setAiOutlines] = useState<ThemeOutline[]>([])
  const [outlineExpanded, setOutlineExpanded] = useState(false)

  // Editable outlines (user can modify after AI generation)
  const [editableOutlines, setEditableOutlines] = useState<Array<{outline_content: string; part: string; page_instruction?: string; page?: number; key_points?: string[]}>>([])

  // Step 1b-2: Chat mode (F2)
  const [outlineMode, setOutlineMode] = useState<'auto' | 'chat'>('auto')
  const [chatMessages, setChatMessages] = useState<Array<{role: 'user'|'assistant'; content: string}>>([])
  const [chatInput, setChatInput] = useState('')
  const [chatLoading, setChatLoading] = useState(false)
  const [chatError, setChatError] = useState('')
  const [chatAccumulated, setChatAccumulated] = useState<ThemeOutline[]>([])

  // Sync AI-generated outlines into editableOutlines when SSE completes
  useEffect(() => {
    if (aiOutlines.length > 0) {
      setEditableOutlines(aiOutlines)
    }
  }, [aiOutlines])

  // Sync chat outlines into editableOutlines
  useEffect(() => {
    if (chatAccumulated.length > 0) {
      setEditableOutlines(chatAccumulated)
      setOutlineExpanded(true)
    }
  }, [chatAccumulated])

  // Step 2 fields
  const [templates, setTemplates] = useState<LayoutTemplate[]>([])
  const [selectedTemplate, setSelectedTemplate] = useState('government_blue')
  const [search, setSearch] = useState('')
  const [cat, setCat] = useState('全部')
  const [templatesLoading, setTemplatesLoading] = useState(true)

  // Step 3 fields
  const [selectedStyle, setSelectedStyle] = useState(0)

  // Load templates
  useEffect(() => {
    if (step !== 2) return
    setTemplatesLoading(true)
    api.getLayouts().then(r => {
      setTemplates(r.data?.templates || [])
      setTemplatesLoading(false)
    }).catch(() => setTemplatesLoading(false))
  }, [step])

  const categories = ['全部', '政府央企', '学术教育', '金融银行', '医疗健康', '科技AI']
  const filteredTemplates = templates.filter(t => {
    const matchCat = cat === '全部' || t.category === cat
    const matchSearch = !search || t.name.includes(search) || t.summary?.includes(search)
    return matchCat && matchSearch
  })

  const handleAnalyze = async () => {
    if (!theme.trim()) { setError('请先填写主题描述'); return }
    setAnalyzing(true)
    setAnalysisError('')
    setAiOutlines([])
    setOutlineExpanded(true)

    // Use local accumulator to avoid stale closure in complete()
    const accumulated: ThemeOutline[] = []

    api.analyzeTheme(theme).subscribe({
      next(event: ThemeOutline) {
        accumulated.push(event)
        setAiOutlines([...accumulated])
      },
      complete() {
        setEditableOutlines(accumulated.map(o => ({
          outline_content: o.outline_content || '',
          part: o.part || '概述',
          page_instruction: o.page_instruction || '',
        })))
        setAnalyzing(false)
      },
      error(err) {
        setAnalysisError(err.message || '网络错误')
        setAnalyzing(false)
      },
    })
  }

  const handleOutlineEdit = (index: number, field: 'outline_content' | 'part', value: string) => {
    setEditableOutlines(prev => {
      const next = [...prev]
      next[index] = { ...next[index], [field]: value }
      return next
    })
  }

  // F2: Chat-based outline generation
  const handleChatSubmit = async () => {
    if (!chatInput.trim()) return
    const userMsg = chatInput.trim()
    const newMessages = [...chatMessages, { role: 'user' as const, content: userMsg }]
    setChatMessages(newMessages)
    setChatInput('')
    setChatLoading(true)
    setChatError('')
    setChatAccumulated([])
    setOutlineExpanded(true)

    const isFinal = userMsg.includes('确定') || userMsg.includes('可以了') || userMsg.includes('完成')

    api.generateOutline(newMessages, isFinal).subscribe({
      next(event: any) {
        if (event.type === 'outline') {
          setChatAccumulated(prev => {
            const next = [...prev]
            next[event.index] = event.data
            return next
          })
        }
        if (event.type === 'complete') {
          // Merge accumulated outlines
          const merged = (event.outlines || chatAccumulated).map((o: any, i: number) => ({
            outline_content: o.outline_content || '',
            part: o.part || '概述',
            page_instruction: o.page_instruction || '',
          }))
          if (merged.length > 0) setEditableOutlines(merged)
          setChatLoading(false)
        }
      },
      error(err) {
        setChatError(err.message || '网络错误')
        setChatLoading(false)
      },
    })
  }

  const handleCreate = async () => {
    if (!name.trim()) { setError('请输入项目名称'); return }
    if (!theme.trim()) { setError('请输入主题描述'); return }
    setLoading(true)
    setError('')
    try {
      const style = QUICK_STYLES[selectedStyle]
      const projRes = await api.createProject({
        name: name.trim(),
        creation_type: 'idea',
        idea_prompt: theme.trim(),
        template_path: selectedTemplate,
        generation_mode: 'guide',
        image_aspect_ratio: '16:9',
        primary_color: style.color,
        font_family: style.font,
        layout_style: 'balanced',
      })
      const pid = projRes.data.project_id

      // Use AI outlines if available, otherwise fallback to default
      // Filter out empty outlines (defense against SSE parsing issues)
      const validEditable = editableOutlines.filter(o => (o.outline_content || '').trim().length > 0)
      const outlines = validEditable.length > 0
        ? validEditable.map((o, i) => ({
            order_index: i,
            outline_content: o.outline_content || '',
            part: o.part || '概述',
            page_instruction: o.page_instruction || '',
          }))
        : DEFAULT_OUTLINES

      await api.createPages(pid, outlines)
      onClose()
      navigate(`/workspace/${pid}`)
    } catch (e: any) {
      setError(e.message || '创建失败')
      setLoading(false)
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-box wizard" onClick={e => e.stopPropagation()}>

        {/* Header */}
        <div className="modal-header">
          <div className="header-step">
            <div className={`step-dot ${step >= 1 ? 'active' : ''}`}>1</div>
            <span className={`step-label ${step === 1 ? 'current' : ''}`}>基本信息</span>
            <div className="step-line" />
            <div className={`step-dot ${step >= 2 ? 'active' : ''}`}>2</div>
            <span className={`step-label ${step === 2 ? 'current' : ''}`}>选择模板</span>
            <div className="step-line" />
            <div className={`step-dot ${step >= 3 ? 'active' : ''}`}>3</div>
            <span className={`step-label ${step === 3 ? 'current' : ''}`}>选择样式</span>
          </div>
          <button className="modal-close" onClick={onClose}><X size={18} /></button>
        </div>

        {/* Step 1: Basic Info */}
        {step === 1 && (
          <div className="step-body">
            <div className="step-icon">
              <Sparkles size={32} color="var(--color-primary)" />
            </div>
            <h2 className="step-title">新建 PPT 项目</h2>
            <p className="step-hint">输入项目主题，AI 将自动规划内容并生成演示文稿</p>

            <div className="form">
              <div className="form-group">
                <label>项目名称</label>
                <input
                  type="text"
                  className="form-input"
                  placeholder="例如：2026年度数字化转型汇报"
                  value={name}
                  onChange={e => setName(e.target.value)}
                  autoFocus
                  onKeyDown={e => e.key === 'Enter' && setStep(2)}
                />
              </div>
              <div className="form-group">
                <label>
                  主题描述
                  <span style={{ fontWeight: 400, color: '#999', marginLeft: 8, fontSize: 12 }}>描述越详细，大纲越精准</span>
                </label>
                <textarea
                  className="form-textarea"
                  placeholder="描述 PPT 的核心内容，例如：包含项目背景、现状分析、实施路径、成果展示、总结展望等部分..."
                  value={theme}
                  onChange={e => setTheme(e.target.value)}
                  rows={4}
                />
              </div>

              {/* AI Outline Section (F2: auto + chat modes) */}
              <div className="ai-outline-section">
                {/* Mode toggle */}
                <div className="outline-mode-toggle">
                  <button
                    className={`mode-btn ${outlineMode === 'auto' ? 'active' : ''}`}
                    onClick={() => { setOutlineMode('auto'); setOutlineExpanded(false); setChatMessages([]); setChatAccumulated([]); }}
                  >
                    <Sparkles size={12} /> 自动生成
                  </button>
                  <button
                    className={`mode-btn ${outlineMode === 'chat' ? 'active' : ''}`}
                    onClick={() => { setOutlineMode('chat'); setOutlineExpanded(false); }}
                  >
                    💬 对话生成
                  </button>
                </div>

                {/* AUTO MODE */}
                {outlineMode === 'auto' && (
                  <>
                    {!outlineExpanded ? (
                      <button
                        className="btn btn-ai-outline"
                        onClick={handleAnalyze}
                        disabled={!theme.trim() || analyzing}
                      >
                        {analyzing ? (
                          <><Loader size={14} className="spin" /> AI 分析中...</>
                        ) : (
                          <><Sparkles size={14} /> AI 生成大纲</>
                        )}
                      </button>
                    ) : null}

                    {/* Inline Outline Preview */}
                    {outlineExpanded && (
                      <div className="outline-preview">
                        <div className="outline-header">
                          <span className="outline-title">
                            {aiOutlines.length > 0
                              ? `AI 生成大纲（共 ${aiOutlines.length} 页）`
                              : analyzing ? '正在分析主题内容...' : '分析结果'}
                          </span>
                          {aiOutlines.length > 0 && (
                            <button
                              className="outline-toggle"
                              onClick={() => setOutlineExpanded(false)}
                            >收起</button>
                          )}
                        </div>

                        {analyzing && aiOutlines.length === 0 && (
                          <div className="outline-loading">
                            <Loader size={16} className="spin-icon" color="var(--color-primary)" />
                            <span>正在理解主题内容并生成结构...</span>
                          </div>
                        )}

                        {analysisError && (
                          <div className="outline-error">{analysisError}</div>
                        )}

                        {(aiOutlines.length > 0 || editableOutlines.length > 0) && (
                          <div className="outline-list">
                            {(aiOutlines.length > 0 ? aiOutlines : editableOutlines).map((o, i) => (
                              <div key={i} className="outline-item">
                                <span className="outline-num">{o.page || i + 1}</span>
                                <div className="outline-content">
                                  <input
                                    className="outline-title-input"
                                    value={editableOutlines[i]?.outline_content || o.outline_content || ''}
                                    onChange={e => handleOutlineEdit(i, 'outline_content', e.target.value)}
                                  />
                                  <div className="outline-meta">
                                    <span className="outline-part">[{o.part || '概述'}]</span>
                                    {o.key_points && o.key_points.length > 0 && (
                                      <span className="outline-points">{o.key_points.join(' · ')}</span>
                                    )}
                                  </div>
                                </div>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                  </>
                )}

                {/* CHAT MODE (F2) */}
                {outlineMode === 'chat' && (
                  <div className="chat-panel">
                    {/* Chat messages */}
                    {chatMessages.length > 0 && (
                      <div className="chat-messages">
                        {chatMessages.map((msg, i) => (
                          <div key={i} className={`chat-msg chat-msg-${msg.role}`}>
                            <span className="chat-msg-role">{msg.role === 'user' ? '我' : 'PPT小助手'}</span>
                            <div className="chat-msg-bubble">{msg.content}</div>
                          </div>
                        ))}
                      </div>
                    )}

                    {/* Outline preview in chat mode */}
                    {(chatAccumulated.length > 0 || editableOutlines.length > 0) && (
                      <div className="chat-outline-preview">
                        <div className="outline-header">
                          <span className="outline-title">
                            {chatAccumulated.length > 0 ? `大纲草稿（共 ${chatAccumulated.length} 页）` : `已生成大纲（${editableOutlines.length} 页）`}
                          </span>
                        </div>
                        <div className="outline-list">
                          {(chatAccumulated.length > 0 ? chatAccumulated : editableOutlines).map((o: any, i) => (
                            <div key={i} className="outline-item">
                              <span className="outline-num">{o.page || i + 1}</span>
                              <div className="outline-content">
                                <input
                                  className="outline-title-input"
                                  value={o.outline_content || ''}
                                  onChange={e => {
                                    const updated = [...(chatAccumulated.length > 0 ? chatAccumulated : editableOutlines)]
                                    updated[i] = { ...updated[i], outline_content: e.target.value }
                                    setEditableOutlines(updated)
                                    if (chatAccumulated.length > 0) setChatAccumulated(updated as any)
                                  }}
                                />
                                <div className="outline-meta">
                                  <span className="outline-part">[{o.part || '概述'}]</span>
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Chat hint */}
                    {chatMessages.length === 0 && (
                      <div className="chat-hint">
                        <p>👋 告诉我你的 PPT 主题，我可以帮你规划结构</p>
                        <p className="chat-hint-example">例如："帮我做一个电网数字化转型的汇报PPT，5-7页"
                        </p>
                      </div>
                    )}

                    {chatError && <div className="outline-error">{chatError}</div>}

                    {chatLoading && (
                      <div className="outline-loading">
                        <Loader size={16} className="spin-icon" color="var(--color-primary)" />
                        <span>PPT小助手正在思考...</span>
                      </div>
                    )}

                    {/* Chat input */}
                    <div className="chat-input-row">
                      <input
                        className="form-input chat-input"
                        placeholder="输入你的要求或修改意见..."
                        value={chatInput}
                        onChange={e => setChatInput(e.target.value)}
                        onKeyDown={e => e.key === 'Enter' && !e.shiftKey && handleChatSubmit()}
                        disabled={chatLoading}
                      />
                      <button
                        className="btn btn-primary chat-send-btn"
                        onClick={handleChatSubmit}
                        disabled={!chatInput.trim() || chatLoading}
                      >
                        {chatLoading ? <Loader size={14} className="spin" /> : '发送'}
                      </button>
                    </div>
                  </div>
                )}
              </div>

              {error && <p className="form-error">{error}</p>}
            </div>

            <div className="step-footer">
              <button
                className="btn btn-primary"
                onClick={() => name.trim() && theme.trim() ? setStep(2) : setError('请填写完整信息')}
              >
                下一步：选模板 <ArrowRight size={15} />
              </button>
            </div>
          </div>
        )}

        {/* Step 2: Template */}
        {step === 2 && (
          <div className="step-body">
            <h2 className="step-title">选择模板</h2>
            <p className="step-hint">{name} — 找到 {filteredTemplates.length} 个模板</p>

            <div className="template-toolbar">
              <input
                type="text"
                className="search-input"
                placeholder="搜索模板..."
                value={search}
                onChange={e => setSearch(e.target.value)}
              />
              <div className="cat-tabs">
                {categories.map(c => (
                  <button key={c} className={`cat-tab ${cat === c ? 'active' : ''}`} onClick={() => setCat(c)}>{c}</button>
                ))}
              </div>
            </div>

            {templatesLoading ? (
              <div className="tmpl-loading">
                <Loader size={24} className="spin-icon" color="var(--color-primary)" />
                <p>加载模板中...</p>
              </div>
            ) : (
              <div className="tmpl-grid">
                {filteredTemplates.map(t => (
                  <div
                    key={t.layout_id}
                    className={`tmpl-card ${selectedTemplate === t.layout_id ? 'selected' : ''}`}
                    onClick={() => setSelectedTemplate(t.layout_id)}
                  >
                    <div className="tmpl-thumb">
                      <Layout size={28} color="rgba(0,51,113,0.3)" />
                      {selectedTemplate === t.layout_id && (
                        <div className="tmpl-check"><Check size={12} color="white" /></div>
                      )}
                    </div>
                    <div className="tmpl-info">
                      <span className="tmpl-name">{t.name}</span>
                      <span className="tmpl-cat">{t.category}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}

            <div className="step-footer">
              <button className="btn btn-secondary" onClick={() => setStep(1)}>
                <ArrowLeft size={14} /> 上一步
              </button>
              <button className="btn btn-primary" onClick={() => setStep(3)}>
                下一步：选样式 <ArrowRight size={15} />
              </button>
            </div>
          </div>
        )}

        {/* Step 3: Style */}
        {step === 3 && (
          <div className="step-body">
            <h2 className="step-title">选择配色风格</h2>
            <p className="step-hint">快速选择一套配色方案，将自动应用到生成的幻灯片</p>

            <div className="style-grid">
              {QUICK_STYLES.map((s, idx) => (
                <div
                  key={s.name}
                  className={`style-card ${selectedStyle === idx ? 'selected' : ''}`}
                  onClick={() => setSelectedStyle(idx)}
                >
                  <div className="style-swatch-row">
                    <div className="style-swatch" style={{ background: s.color }} />
                    <div className="style-swatch accent" style={{ background: '#00875A' }} />
                    <div className="style-swatch light" style={{ background: '#F4F7FA' }} />
                  </div>
                  <div className="style-info">
                    <span className="style-name">{s.name}</span>
                    {selectedStyle === idx && (
                      <span className="style-check"><Check size={11} color="white" /></span>
                    )}
                  </div>
                </div>
              ))}
            </div>

            {/* Preview */}
            <div className="style-preview" style={{ borderTopColor: QUICK_STYLES[selectedStyle].color }}>
              <div className="preview-label">预览效果</div>
              <div className="preview-slide" style={{ background: QUICK_STYLES[selectedStyle].color }}>
                <span style={{ color: 'white', fontWeight: 700, fontSize: 18 }}>Aa</span>
                <span style={{ color: 'rgba(255,255,255,0.75)', fontSize: 13 }}>{name || '项目标题'}</span>
              </div>
              <div className="preview-slide white">
                <div style={{ background: QUICK_STYLES[selectedStyle].color, height: 6, width: 80, borderRadius: 3 }} />
                <div style={{ background: '#E2E8F0', height: 8, width: '80%', borderRadius: 4, marginTop: 12 }} />
                <div style={{ background: '#E2E8F0', height: 8, width: '60%', borderRadius: 4, marginTop: 8 }} />
              </div>
            </div>

            {error && <p className="form-error">{error}</p>}

            <div className="step-footer">
              <button className="btn btn-secondary" onClick={() => setStep(2)}>
                <ArrowLeft size={14} /> 上一步
              </button>
              <button className="btn btn-primary" onClick={handleCreate} disabled={loading}>
                {loading ? <><Loader size={14} className="spin" /> 创建中...</> : <><Sparkles size={14} /> 创建项目并生成</>}
              </button>
            </div>
          </div>
        )}

      </div>

      <style>{`
        .modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; z-index: 1000; backdrop-filter: blur(3px); }
        .modal-box { background: white; border-radius: 16px; width: 640px; max-width: 95vw; max-height: 92vh; overflow: hidden; display: flex; flex-direction: column; box-shadow: 0 24px 64px rgba(0,0,0,0.2); }
        .modal-header { display: flex; align-items: center; justify-content: space-between; padding: 20px 28px; border-bottom: 1px solid var(--color-border); background: var(--color-bg-subtle); }
        .header-step { display: flex; align-items: center; gap: 10px; }
        .step-dot { width: 26px; height: 26px; border-radius: 50%; background: var(--color-border); color: var(--color-text-muted); font-size: 12px; font-weight: 700; display: flex; align-items: center; justify-content: center; transition: all 0.2s; }
        .step-dot.active { background: var(--color-primary); color: white; }
        .step-label { font-size: 13px; color: var(--color-text-muted); font-weight: 500; }
        .step-label.current { color: var(--color-primary); font-weight: 600; }
        .step-line { width: 32px; height: 2px; background: var(--color-border); }
        .modal-close { width: 30px; height: 30px; border-radius: 6px; border: none; background: var(--color-bg-subtle); color: var(--color-text-muted); cursor: pointer; display: flex; align-items: center; justify-content: center; }
        .step-body { padding: 28px; overflow-y: auto; flex: 1; display: flex; flex-direction: column; gap: 20px; }
        .step-icon { width: 56px; height: 56px; background: #EBF5FF; border-radius: 14px; display: flex; align-items: center; justify-content: center; }
        .step-title { font-size: 20px; font-weight: 700; color: var(--color-text); margin: -8px 0 -4px; }
        .step-hint { font-size: 13px; color: var(--color-text-muted); margin-top: -8px; }
        .form { display: flex; flex-direction: column; gap: 16px; }
        .form-group { display: flex; flex-direction: column; gap: 6px; }
        .form-group label { font-size: 13px; font-weight: 600; color: var(--color-text); }
        .form-input, .form-textarea { padding: 10px 14px; border: 1.5px solid var(--color-border); border-radius: 8px; font-size: 14px; font-family: inherit; outline: none; transition: border-color 0.2s; }
        .form-input:focus, .form-textarea:focus { border-color: var(--color-primary); }
        .form-textarea { resize: vertical; }
        .form-error { color: #DC2626; font-size: 13px; }
        .ai-outline-section { display: flex; flex-direction: column; gap: 10px; }
        .btn-ai-outline { background: linear-gradient(135deg, #003371, #005691); color: white; align-self: flex-start; font-size: 13px; padding: 8px 16px; }
        .btn-ai-outline:hover:not(:disabled) { opacity: 0.9; }
        .btn-ai-outline:disabled { opacity: 0.5; cursor: not-allowed; }
        .outline-preview { background: #F8FAFF; border: 1.5px solid #E2E8F0; border-radius: 10px; padding: 14px; display: flex; flex-direction: column; gap: 10px; }
        .outline-header { display: flex; align-items: center; justify-content: space-between; }
        .outline-title { font-size: 13px; font-weight: 600; color: var(--color-primary); }
        .outline-toggle { font-size: 12px; color: #999; background: none; border: none; cursor: pointer; padding: 2px 6px; }
        .outline-toggle:hover { color: var(--color-primary); }
        .outline-loading { display: flex; align-items: center; gap: 8px; font-size: 13px; color: #666; padding: 8px 0; }
        .outline-error { color: #DC2626; font-size: 12px; padding: 6px 10px; background: #FEF2F2; border-radius: 6px; }
        .outline-list { display: flex; flex-direction: column; gap: 6px; max-height: 280px; overflow-y: auto; }
        .outline-item { display: flex; align-items: flex-start; gap: 10px; padding: 8px; background: white; border-radius: 6px; border: 1px solid #E5E7EB; }
        .outline-num { min-width: 24px; height: 24px; background: var(--color-primary); color: white; border-radius: 50%; font-size: 11px; font-weight: 700; display: flex; align-items: center; justify-content: center; flex-shrink: 0; margin-top: 1px; }
        .outline-content { flex: 1; display: flex; flex-direction: column; gap: 3px; }
        .outline-title-input { font-size: 13px; font-weight: 600; color: #333; border: none; background: transparent; width: 100%; outline: none; padding: 2px 4px; border-radius: 4px; }
        .outline-title-input:focus { background: #EBF5FF; }
        .outline-meta { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
        .outline-part { font-size: 11px; color: var(--color-primary); background: #EBF5FF; padding: 1px 6px; border-radius: 10px; font-weight: 500; }
        .outline-points { font-size: 11px; color: #999; }
        .outline-mode-toggle { display: flex; gap: 8px; align-self: flex-start; }
        .mode-btn { display: inline-flex; align-items: center; gap: 5px; padding: 6px 14px; border-radius: 20px; border: 1.5px solid var(--color-border); background: white; font-size: 12px; font-weight: 500; color: var(--color-text-muted); cursor: pointer; transition: all 0.15s; }
        .mode-btn.active { background: var(--color-primary); color: white; border-color: var(--color-primary); }
        .chat-panel { background: #F8FAFF; border: 1.5px solid #E2E8F0; border-radius: 10px; padding: 14px; display: flex; flex-direction: column; gap: 10px; }
        .chat-messages { display: flex; flex-direction: column; gap: 8px; max-height: 160px; overflow-y: auto; }
        .chat-msg { display: flex; flex-direction: column; gap: 3px; }
        .chat-msg-user { align-items: flex-end; }
        .chat-msg-assistant { align-items: flex-start; }
        .chat-msg-role { font-size: 10px; color: #999; font-weight: 600; }
        .chat-msg-bubble { max-width: 85%; padding: 8px 12px; border-radius: 10px; font-size: 13px; line-height: 1.5; }
        .chat-msg-user .chat-msg-bubble { background: var(--color-primary); color: white; border-bottom-right-radius: 2px; }
        .chat-msg-assistant .chat-msg-bubble { background: white; border: 1px solid #E2E8F0; border-bottom-left-radius: 2px; }
        .chat-hint { text-align: center; padding: 12px; color: #666; font-size: 13px; }
        .chat-hint-example { font-size: 12px; color: #999; margin-top: 4px; }
        .chat-outline-preview { background: white; border: 1px solid #E2E8F0; border-radius: 8px; padding: 10px; }
        .chat-input-row { display: flex; gap: 8px; align-items: center; }
        .chat-input { flex: 1; }
        .chat-send-btn { padding: 9px 16px; white-space: nowrap; }
        .step-footer { display: flex; justify-content: flex-end; gap: 10px; margin-top: auto; padding-top: 8px; }
        .btn { display: inline-flex; align-items: center; gap: 6px; padding: 9px 20px; border-radius: 8px; font-size: 14px; font-weight: 600; cursor: pointer; border: none; transition: all 0.2s; }
        .btn-primary { background: var(--color-primary); color: white; }
        .btn-primary:hover { background: var(--color-primary-light); }
        .btn-primary:disabled { opacity: 0.7; cursor: not-allowed; }
        .btn-secondary { background: white; color: var(--color-text); border: 1.5px solid var(--color-border); }
        .btn-secondary:hover { background: var(--color-bg-subtle); }
        .spin { animation: spin 1s linear infinite; }
        @keyframes spin { to { transform: rotate(360deg); } }
        .template-toolbar { display: flex; flex-direction: column; gap: 10px; }
        .search-input { padding: 8px 14px; border: 1.5px solid var(--color-border); border-radius: 8px; font-size: 13px; font-family: inherit; outline: none; }
        .search-input:focus { border-color: var(--color-primary); }
        .cat-tabs { display: flex; gap: 6px; flex-wrap: wrap; }
        .cat-tab { padding: 4px 12px; border-radius: 20px; border: 1px solid var(--color-border); background: white; font-size: 12px; color: var(--color-text-muted); cursor: pointer; }
        .cat-tab.active { background: var(--color-primary); color: white; border-color: var(--color-primary); }
        .tmpl-loading { display: flex; flex-direction: column; align-items: center; gap: 10px; padding: 40px; color: var(--color-text-muted); }
        .spin-icon { animation: spin 1s linear infinite; }
        .tmpl-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; max-height: 300px; overflow-y: auto; }
        .tmpl-card { border: 2px solid var(--color-border); border-radius: 8px; overflow: hidden; cursor: pointer; transition: all 0.15s; position: relative; }
        .tmpl-card:hover { border-color: var(--color-primary-light); transform: translateY(-1px); }
        .tmpl-card.selected { border-color: var(--color-primary); }
        .tmpl-thumb { width: 100%; aspect-ratio: 16/9; background: var(--color-bg-subtle); display: flex; align-items: center; justify-content: center; position: relative; }
        .tmpl-check { position: absolute; top: 5px; right: 5px; width: 20px; height: 20px; background: var(--color-primary); border-radius: 50%; display: flex; align-items: center; justify-content: center; }
        .tmpl-info { padding: 8px 10px; display: flex; flex-direction: column; gap: 1px; }
        .tmpl-name { font-size: 12px; font-weight: 600; color: var(--color-text); }
        .tmpl-cat { font-size: 10px; color: var(--color-primary); font-weight: 500; }
        .style-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; }
        .style-card { border: 2px solid var(--color-border); border-radius: 10px; padding: 12px; cursor: pointer; transition: all 0.15s; }
        .style-card:hover { border-color: var(--color-primary-light); }
        .style-card.selected { border-color: var(--color-primary); background: #EBF5FF; }
        .style-swatch-row { display: flex; gap: 4px; margin-bottom: 8px; }
        .style-swatch { flex: 1; height: 28px; border-radius: 5px; }
        .style-swatch.accent { flex: 0.4; }
        .style-swatch.light { flex: 0.8; background: #F4F7FA; border: 1px solid #E2E8F0; }
        .style-info { display: flex; align-items: center; justify-content: space-between; }
        .style-name { font-size: 12px; font-weight: 600; color: var(--color-text); }
        .style-check { width: 18px; height: 18px; background: var(--color-primary); border-radius: 50%; display: flex; align-items: center; justify-content: center; }
        .style-preview { border-top: 3px solid; margin-top: 4px; padding-top: 14px; display: flex; gap: 10px; align-items: center; }
        .preview-label { font-size: 12px; color: var(--color-text-muted); writing-mode: vertical-rl; transform: rotate(180deg); }
        .preview-slide { flex: 1; border-radius: 6px; padding: 14px; display: flex; flex-direction: column; gap: 4px; }
        .preview-slide.white { background: white; border: 1px solid var(--color-border); }
      `}</style>
    </div>
  )
}

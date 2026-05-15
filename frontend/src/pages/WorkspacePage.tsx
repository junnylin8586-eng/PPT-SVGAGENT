import { useEffect, useState, useCallback, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, RefreshCw, Download, Eye, Layout, CheckCircle, Edit3, Plus, Trash2, Palette, Loader, Save, Settings } from 'lucide-react'
import { useProjectStore } from '@/store/projectStore'
import { api, type Page, type LayoutTemplate } from '@/api/client'
import GenerationProgress from '@/components/workspace/GenerationProgress'
import TemplateSelectorModal from '@/components/template/TemplateSelectorModal'
import ExportDialog from '@/components/workspace/ExportDialog'
import PageEditorModal from '@/components/workspace/PageEditorModal'
import OutlineEditorModal from '@/components/workspace/OutlineEditorModal'
import StyleSettingsModal from '@/components/workspace/StyleSettingsModal'
import SettingsModal from '@/components/settings/SettingsModal'

type GenStatus = 'idle' | 'generating' | 'completed' | 'error'

export default function WorkspacePage() {
  const { projectId } = useParams<{ projectId: string }>()
  const navigate = useNavigate()
  const { currentProject, setCurrentProject } = useProjectStore()

  const [pages, setPages] = useState<Page[]>([])
  const [templates, setTemplates] = useState<LayoutTemplate[]>([])
  const [selectedTemplate, setSelectedTemplate] = useState('government_blue')
  const [loading, setLoading] = useState(true)
  const [genStatus, setGenStatus] = useState<GenStatus>('idle')
  const [genError, setGenError] = useState('')
  const [currentGenIdx, setCurrentGenIdx] = useState(-1)
  const [completedDismissed, setCompletedDismissed] = useState(false)
  const [selectedPage, setSelectedPage] = useState<Page | null>(null)
  const [svgContents, setSvgContents] = useState<Record<string, string>>({})
  const [showTemplateModal, setShowTemplateModal] = useState(false)
  const [showExport, setShowExport] = useState(false)
  const [showPageEditor, setShowPageEditor] = useState(false)
  const [showOutlineEditor, setShowOutlineEditor] = useState(false)
  const [showStyleSettings, setShowStyleSettings] = useState(false)
  const [showSettings, setShowSettings] = useState(false)
  const [regeneratingPageId, setRegeneratingPageId] = useState<string | null>(null)
  const [loadingPageId, setLoadingPageId] = useState<string | null>(null)
  const [savingAll, setSavingAll] = useState(false)
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null)
  // Use ref to avoid stale closure in polling interval
  const svgContentsRef = useRef<Record<string, string>>({})
  const updateSvgContents = useCallback(( updater: (prev: Record<string, string>) => Record<string, string>) => {
    setSvgContents(prev => {
      const next = typeof updater === 'function' ? updater(prev) : updater
      svgContentsRef.current = next
      return next
    })
  }, [])

  const loadProject = useCallback(async () => {
    if (!projectId) return
    try {
      const res = await api.getProject(projectId)
      setCurrentProject(res.data)
      setSelectedTemplate(res.data.template_path || 'government_blue')
      const pageRes = await api.getPages(projectId)
      const pageList = pageRes.data || []
      setPages(pageList)
      if (pageList.length > 0 && !selectedPage) setSelectedPage(pageList[0])
    } catch { navigate('/') }
  }, [projectId, navigate, setCurrentProject, selectedPage])

  useEffect(() => {
    if (!projectId) return
    Promise.all([
      loadProject(),
      api.getLayouts().then(r => setTemplates(r.data?.templates || [])),
    ]).finally(() => setLoading(false))
  }, [projectId, loadProject])

  const loadSvgContent = useCallback(async (page: Page) => {
    const existing = svgContentsRef.current[page.page_id]
    if (page.svg_path && !existing) {
      setLoadingPageId(page.page_id)
      try {
        const filename = page.svg_path.split('/').pop()
        const res = await fetch(`${api.getFileUrl(`${projectId}/${filename}`)}?_t=${Date.now()}`)
        if (res.ok) {
          const text = await res.text()
          updateSvgContents(prev => ({ ...prev, [page.page_id]: text }))
        }
      } catch (err) {
        console.error('[loadSvgContent] Failed to load SVG for page', page.page_id, page.svg_path, err)
      } finally {
        setLoadingPageId(prev => prev === page.page_id ? null : prev)
      }
    }
  }, [projectId, updateSvgContents])

  // Clear SVG cache when generation starts, so old slides don't linger
  useEffect(() => {
    if (genStatus === 'generating') {
      setSvgContents({})
      svgContentsRef.current = {}
    }
  }, [genStatus])

  // Reload all SVGs when generation completes
  useEffect(() => {
    if (genStatus !== 'completed') return
    let cancelled = false
    const reload = async () => {
      const pageRes = await api.getPages(projectId!)
      if (cancelled) return
      const updated: Page[] = pageRes.data || []
      setPages(updated)
      await Promise.all(updated.filter(p => p.status === 'GENERATED' && p.svg_path).map(p => loadSvgContent(p)))
    }
    reload()
    return () => { cancelled = true }
  }, [genStatus, projectId, loadSvgContent])

  useEffect(() => {
    pages.filter(p => p.svg_path && !svgContents[p.page_id] && !loadingPageId).forEach(loadSvgContent)
  }, [pages, loadSvgContent, svgContents, loadingPageId])

  // Poll for generation status — update each completed page's SVG immediately
  useEffect(() => {
    if (genStatus !== 'generating') return
    pollingRef.current = setInterval(async () => {
      try {
        const res = await api.getPages(projectId!)
        const updated: Page[] = res.data || []
        setPages(updated)

        // Immediately load SVGs for any newly completed pages
        updated.forEach(p => {
          if (p.status === 'GENERATED' && p.svg_path && !svgContentsRef.current[p.page_id] && !loadingPageId) {
            loadSvgContent(p)
          }
        })

        const genIdx = updated.findIndex((p: Page) => p.status === 'GENERATING' || p.status === 'PENDING')
        if (genIdx === -1) {
          clearInterval(pollingRef.current!)
          setGenStatus('completed')
          setCurrentGenIdx(-1)
          await loadProject()
        } else {
          setCurrentGenIdx(genIdx)
        }
      } catch { /* ignore */ }
    }, 3000)
    return () => { if (pollingRef.current) clearInterval(pollingRef.current!) }
  }, [genStatus, projectId, loadProject, loadingPageId, loadSvgContent])

  const handleGenerate = async () => {
    if (!projectId) return
    setGenStatus('generating')
    setGenError('')
    setCurrentGenIdx(0)
    setCompletedDismissed(false)
    try {
      // Always refresh pages from API first — ensures all pages
      // (newly added, edited, unsaved) are included in generation
      const pageRes = await api.getPages(projectId)
      const latestPages: Page[] = pageRes.data || []
      setPages(latestPages)

      const freshProject = await api.getProject(projectId)
      const latestProject = freshProject.data
      await api.updateProject(projectId, {
        template_path: selectedTemplate,
        primary_color: latestProject.primary_color,
        font_family: latestProject.font_family,
        layout_style: latestProject.layout_style,
      })

      // Generate SVGs for ALL existing pages — no per-page confirmation needed
      // Backend is synchronous: all pages are generated before response returns
      await api.generate(projectId, selectedTemplate)

      // Bug Fix: Immediately reload data after synchronous generation completes,
      // instead of waiting for the 3-second polling interval.
      const freshPages = await api.getPages(projectId)
      const freshPagesList: Page[] = freshPages.data || []
      setPages(freshPagesList)
      // Load all SVGs immediately — use Promise.all to ensure completion
      const svgPages = freshPagesList.filter(p => p.status === 'GENERATED' && p.svg_path)
      if (svgPages.length > 0) {
        await Promise.all(svgPages.map(p => loadSvgContent(p)))
      }
      // Skip polling if everything is already done
      const pendingIdx = freshPagesList.findIndex((p: Page) => p.status === 'GENERATING' || p.status === 'PENDING')
      if (pendingIdx === -1) {
        setGenStatus('completed')
        setCurrentGenIdx(-1)
        await loadProject()
      }
    } catch (e: any) {
      setGenStatus('error')
      setGenError(e.message || '生成失败')
    }
  }

  const handleDeletePage = async (page: Page, e: React.MouseEvent) => {
    e.stopPropagation()
    if (!confirm('确定删除此页面？')) return
    try {
      await fetch(`${import.meta.env.DEV ? '/api' : ''}/api/ppt/projects/${projectId}/pages/${page.page_id}`, { method: 'DELETE' })
      setPages(prev => prev.filter(p => p.page_id !== page.page_id))
      if (selectedPage?.page_id === page.page_id) setSelectedPage(null)
    } catch { /* ignore */ }
  }

  const handleAddPage = async () => {
    if (!projectId) return
    const newIndex = pages.length
    const newOutline = { order_index: newIndex, outline_content: '新页面', part: '概述' }
    try {
      await api.createPages(projectId, [newOutline])
      await loadProject()
      // Auto-select the newly created page
      const pageRes = await api.getPages(projectId)
      const newPage = (pageRes.data || []).find((p: Page) => p.order_index === newIndex)
      if (newPage) setSelectedPage(newPage)
    } catch { /* ignore */ }
  }

  const handleSaveAllPages = async () => {
    if (!projectId || pages.length === 0) return
    setSavingAll(true)
    try {
      const outlines = pages.map(p => ({
        order_index: p.order_index,
        outline_content: p.outline_content || '',
        part: p.part || '',
        page_instruction: p.description_content || '',
      }))
      await api.createPages(projectId!, outlines)
      await loadProject()
    } catch (e) {
      console.error('批量保存失败', e)
    } finally {
      setSavingAll(false)
    }
  }

  const handleRegeneratePage = async (page: Page, e?: React.MouseEvent) => {
    if (e) e.stopPropagation()
    if (!projectId) return
    setRegeneratingPageId(page.page_id)
    try {
      await api.generatePage(projectId, page.page_id, selectedTemplate)
      // 强制重新拉取最新页面列表（含 svg_path 更新）
      const pageRes = await api.getPages(projectId)
      const updatedPage = (pageRes.data || []).find((p: Page) => p.page_id === page.page_id)
      if (updatedPage?.svg_path) {
        const filename = updatedPage.svg_path.split('/').pop()
        const fres = await fetch(`${api.getFileUrl(`${projectId}/${filename}`)}?_t=${Date.now()}`)
        if (fres.ok) {
          const text = await fres.text()
          // Bug Fix: Use updateSvgContents to keep svgContentsRef in sync
          // (raw setSvgContents bypasses the ref update)
          updateSvgContents(prev => ({ ...prev, [page.page_id]: text }))
        } else {
          console.error('[regenerate] SVG fetch failed:', fres.status, fres.statusText)
        }
      } else {
        console.error('[regenerate] Updated page has no svg_path:', updatedPage)
      }
      setPages(pageRes.data || [])
    } catch (err) {
      console.error('[regenerate] 单页生成失败', err)
    } finally {
      setRegeneratingPageId(null)
    }
  }

  if (loading) {
    return (
      <div className="loading-center">
        <div className="spinner" />
        <p>加载中...</p>
      </div>
    )
  }

  const project = currentProject
  const generatedCount = pages.filter(p => p.status === 'GENERATED').length
  const selectedIdx = selectedPage ? pages.findIndex(p => p.page_id === selectedPage.page_id) : -1

  return (
    <div className="workspace">
      {/* Topbar */}
      <div className="workspace-topbar">
        <button className="btn-back" onClick={() => navigate('/')}>
          <ArrowLeft size={18} /> 返回
        </button>
        <div className="topbar-info">
          <h1 className="topbar-title">{project?.name || '工作区'}</h1>
          <span className="page-count-badge">
            {generatedCount > 0 ? `${generatedCount}/${pages.length} 页已生成` : `${pages.length} 页`}
          </span>
        </div>
        <div className="topbar-divider" />
        <div className="topbar-actions">
          <div className="toolbar-group">
            <button className="tool-btn" onClick={() => setShowOutlineEditor(true)} title="编辑大纲">
              <Edit3 size={15} /> 大纲
            </button>
            <button className="tool-btn" onClick={() => setShowStyleSettings(true)} title="样式设置">
              <Palette size={15} /> 样式
            </button>
            <button className="tool-btn" onClick={() => setShowSettings(true)} title="AI 设置">
              <Settings size={15} /> 设置
            </button>
            <button className="tool-btn" onClick={() => setShowTemplateModal(true)} title="更换模板">
              <Layout size={15} /> 模板
            </button>
          </div>
          <div className="toolbar-divider" />
          <div className="toolbar-group">
            <button
              className="btn btn-primary"
              onClick={handleGenerate}
              disabled={genStatus === 'generating'}
            >
              <RefreshCw size={14} className={genStatus === 'generating' ? 'spin' : ''} />
              {genStatus === 'generating' ? '生成中...' : '开始生成'}
            </button>
            {generatedCount > 0 && (
              <button className="btn btn-green" onClick={() => setShowExport(true)}>
                <Download size={14} /> 导出
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Body */}
      <div className="workspace-body">
        {/* Left Panel */}
        <div className="page-list-panel" style={{ position: 'relative' }}>
          {genStatus === 'generating' && (
            <div className="gen-fullscreen-overlay">
              <GenerationProgress pages={pages} currentIndex={currentGenIdx} status={genStatus} error={genError} />
            </div>
          )}
          {genStatus === 'completed' && !completedDismissed && (
            <div className="gen-complete-overlay">
              <div className="gen-complete-card">
                <CheckCircle size={40} color="#00875A" />
                <span style={{ fontSize: 16, fontWeight: 600, color: '#00875A' }}>全部幻灯片生成完成</span>
                <span style={{ fontSize: 13, color: '#666' }}>{pages.length} 页已就绪</span>
                <button className="btn btn-primary" style={{ marginTop: 8 }} onClick={() => { setGenStatus('idle'); setCompletedDismissed(false) }}>查看结果</button>
              </div>
            </div>
          )}
          {genStatus === 'idle' && (
            <div className="panel-section">
              <div className="panel-header-row">
                <span>幻灯片</span>
              </div>
            </div>
          )}

          <div className="panel-section panel-section-pages">
            <div className="panel-header-row">
              <span>幻灯片</span>
              <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
                <button className="link-btn" onClick={handleAddPage} title="添加页面">
                  <Plus size={12} />
                </button>
                <button
                  className={`link-btn${savingAll ? ' saving' : ''}`}
                  onClick={handleSaveAllPages}
                  title="确认所有页面（批量保存大纲和描述）"
                  disabled={savingAll}
                >
                  <Save size={12} className={savingAll ? 'spin' : ''} />
                </button>
                <button className="link-btn" onClick={() => setShowOutlineEditor(true)} title="编辑大纲">
                  <Edit3 size={12} />
                </button>
                <span className="panel-count">{pages.length} 页</span>
              </div>
            </div>
            <div className="page-list">
              {pages.map((page, idx) => {
                const isSelected = selectedPage?.page_id === page.page_id
                const isDone = page.status === 'GENERATED' || page.status === 'DESCRIPTION_GENERATED'
                return (
                  <div
                    key={page.page_id}
                    className={`page-list-item ${isSelected ? 'active' : ''} ${isDone ? 'done' : ''}`}
                    onClick={() => { setSelectedPage(page); loadSvgContent(page) }}
                  >
                    <div className="page-thumb-small">
                      {(isDone || loadingPageId === page.page_id) ? (
                        svgContents[page.page_id] && loadingPageId !== page.page_id ? (
                          <div className="svg-thumb-wrap">
                            <div className="svg-thumb-inner" dangerouslySetInnerHTML={{ __html: svgContents[page.page_id] }} />
                          </div>
                        ) : (
                          <div className="thumb-placeholder-sm">
                            {loadingPageId === page.page_id
                              ? <Loader size={14} color="rgba(255,255,255,0.9)" className="spin" />
                              : <CheckCircle size={14} color="rgba(255,255,255,0.8)" />
                            }
                          </div>
                        )
                      ) : (
                        <div className="thumb-placeholder-sm">
                          <Layout size={16} color="rgba(255,255,255,0.35)" />
                        </div>
                      )}
                    </div>
                    <div className="page-meta">
                      <span className="page-num-label">第 {idx + 1} 页</span>
                      <span className="page-part-label">{page.outline_content || page.part || ''}</span>
                    </div>
                    <div className="page-actions">
                      <button
                        className="page-action-btn"
                        onClick={e => { e.stopPropagation(); setSelectedPage(page); setShowPageEditor(true) }}
                        title="编辑此页"
                      >
                        <Edit3 size={11} />
                      </button>
                      <button
                        className="page-action-btn"
                        onClick={e => handleRegeneratePage(page, e)}
                        title="重新生成"
                        disabled={regeneratingPageId === page.page_id}
                      >
                        <RefreshCw size={11} className={regeneratingPageId === page.page_id ? 'spin' : ''} />
                      </button>
                      <button
                        className="page-action-btn danger"
                        onClick={e => handleDeletePage(page, e)}
                        title="删除此页"
                      >
                        <Trash2 size={11} />
                      </button>
                    </div>
                  </div>
                )
              })}

              {pages.length === 0 && (
                <div className="empty-pages">
                  <p>暂无页面</p>
                  <button className="btn btn-primary" style={{ fontSize: '12px', padding: '5px 12px' }} onClick={() => setShowOutlineEditor(true)}>
                    <Plus size={12} /> 添加页面
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Right Preview */}
        <div className="preview-panel">
          {selectedPage && svgContents[selectedPage.page_id] && loadingPageId !== selectedPage.page_id ? (
            <div className="preview-wrapper">
              <div className="preview-label">
                <Eye size={13} color="#666" />
                <span>第 {selectedIdx + 1} 页</span>
                <span className="preview-part">{selectedPage.part || selectedPage.outline_content?.slice(0, 20)}</span>
                <button
                  className="edit-page-btn"
                  onClick={() => setShowPageEditor(true)}
                >
                  <Edit3 size={12} /> 编辑
                </button>
              </div>
              <div className="svg-preview">
                <div className="svg-content" dangerouslySetInnerHTML={{ __html: svgContents[selectedPage.page_id] }} />
              </div>
            </div>
          ) : selectedPage ? (
            <div className="preview-loading">
              <div className="spinner" />
              <p>{loadingPageId === selectedPage.page_id ? '加载新幻灯片中...' : '预览加载中...'}</p>
            </div>
          ) : (
            <div className="preview-empty">
              <svg width="80" height="80" viewBox="0 0 80 80" fill="none">
                <rect x="10" y="15" width="60" height="50" rx="4" fill="#EBF5FF" stroke="#003371" strokeWidth="2"/>
                <rect x="17" y="24" width="30" height="5" rx="2.5" fill="#003371" opacity="0.4"/>
                <rect x="17" y="33" width="46" height="3" rx="1.5" fill="#003371" opacity="0.2"/>
                <rect x="17" y="40" width="36" height="3" rx="1.5" fill="#003371" opacity="0.2"/>
                <rect x="17" y="47" width="26" height="3" rx="1.5" fill="#003371" opacity="0.2"/>
              </svg>
              <p className="preview-empty-text">选择左侧幻灯片预览</p>
              {pages.length === 0 && (
                <button className="btn btn-primary" onClick={() => setShowOutlineEditor(true)}>
                  <Plus size={14} /> 添加页面
                </button>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Modals */}
      <TemplateSelectorModal
        open={showTemplateModal}
        selected={selectedTemplate}
        onSelect={id => setSelectedTemplate(id)}
        onClose={() => setShowTemplateModal(false)}
      />
      {showExport && project && (
        <ExportDialog
          open={showExport}
          projectId={projectId!}
          projectName={project.name}
          pages={pages}
          onClose={() => setShowExport(false)}
        />
      )}
      {showPageEditor && selectedPage && (
        <PageEditorModal
          open={showPageEditor}
          page={selectedPage}
          pageIndex={selectedIdx}
          projectId={projectId!}
          onClose={() => setShowPageEditor(false)}
          onSaved={loadProject}
        />
      )}
      {showOutlineEditor && (
        <OutlineEditorModal
          open={showOutlineEditor}
          projectId={projectId!}
          initialPages={pages.map(p => ({ page_id: p.page_id, order_index: p.order_index, part: p.part || '', outline_content: p.outline_content || '' }))}
          onClose={() => setShowOutlineEditor(false)}
          onSaved={loadProject}
        />
      )}
      {showStyleSettings && project && (
        <StyleSettingsModal
          open={showStyleSettings}
          projectId={projectId!}
          initial={{
            primary_color: project.primary_color || '#003371',
            font_family: project.font_family || 'system-ui',
            layout_style: project.layout_style || 'balanced',
          }}
          onClose={() => setShowStyleSettings(false)}
          onSaved={loadProject}
        />
      )}
      {showSettings && (
        <SettingsModal
          open={showSettings}
          onClose={() => setShowSettings(false)}
          onSaved={() => {}}
        />
      )}

      <style>{`
        .workspace { display: flex; flex-direction: column; height: calc(100vh - 56px); }
        .workspace-topbar { display: flex; align-items: center; gap: 0; padding: 10px 20px; background: white; border-bottom: 1px solid var(--color-border); flex-shrink: 0; }
        .btn-back { display: flex; align-items: center; gap: 6px; padding: 7px 14px; border-radius: 6px; border: 1px solid var(--color-border); background: white; color: var(--color-text-muted); font-size: 13px; cursor: pointer; transition: all 0.15s; flex-shrink: 0; }
        .btn-back:hover { background: var(--color-bg-subtle); color: var(--color-text); }
        .topbar-info { flex: 1; display: flex; align-items: center; gap: 10px; padding: 0 16px; min-width: 0; }
        .topbar-title { font-size: 15px; font-weight: 600; color: var(--color-text); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .page-count-badge { font-size: 12px; color: var(--color-text-muted); background: var(--color-bg-subtle); padding: 2px 10px; border-radius: 10px; white-space: nowrap; flex-shrink: 0; }
        .topbar-divider { width: 1px; height: 28px; background: var(--color-border); flex-shrink: 0; margin: 0 4px; }
        .topbar-actions { display: flex; align-items: center; gap: 8px; flex-shrink: 0; }
        .toolbar-group { display: flex; align-items: center; gap: 2px; }
        .toolbar-divider { width: 1px; height: 22px; background: var(--color-border); margin: 0 4px; }
        .tool-btn { display: inline-flex; align-items: center; gap: 5px; padding: 7px 12px; border-radius: 6px; border: none; background: transparent; color: var(--color-text-muted); font-size: 13px; cursor: pointer; transition: all 0.15s; }
        .tool-btn:hover { background: var(--color-bg-subtle); color: var(--color-text); }
        .tool-btn:active { background: var(--color-border); }
        .btn { display: inline-flex; align-items: center; gap: 6px; padding: 7px 16px; border-radius: 6px; font-size: 13px; font-weight: 500; cursor: pointer; transition: all 0.2s; border: none; }
        .btn-primary { background: var(--color-primary); color: white; }
        .btn-primary:hover { background: var(--color-primary-light); }
        .btn-primary:disabled { opacity: 0.7; cursor: not-allowed; }
        .btn-green { background: #00875A; color: white; }
        .btn-green:hover { background: #006B47; }
        .spin { animation: spin 1s linear infinite; }
        @keyframes spin { to { transform: rotate(360deg); } }
        .workspace-body { flex: 1; display: flex; overflow: hidden; }
        .page-list-panel { width: 270px; flex-shrink: 0; border-right: 1px solid var(--color-border); background: white; display: flex; flex-direction: column; overflow: hidden; }
        .panel-section { padding: 10px 14px; border-bottom: 1px solid var(--color-border); }
        .panel-section:last-child { flex: 1; display: flex; flex-direction: column; min-height: 0; overflow: hidden; }
        .panel-section-pages { flex: 1; display: flex; flex-direction: column; min-height: 0; overflow: hidden; }
        .panel-header-row { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; flex-shrink: 0; }
        .panel-header-row > span { font-size: 12px; font-weight: 600; color: var(--color-text); }
        .link-btn { background: none; border: none; color: var(--color-primary); cursor: pointer; padding: 2px; display: flex; align-items: center; }
        .link-btn:hover { opacity: 0.8; }
        .panel-count { font-size: 11px; color: var(--color-text-muted); }
        .page-list { flex: 1; overflow-y: auto; display: flex; flex-direction: column; gap: 5px; padding: 6px; min-height: 0; }
        .page-list-item { display: flex; gap: 8px; padding: 8px; border-radius: 8px; cursor: pointer; border: 2px solid transparent; transition: all 0.15s; align-items: center; }
        .page-list-item:hover { background: var(--color-bg-subtle); }
        .page-list-item.active { border-color: var(--color-primary); background: #EBF5FF; }
        .page-list-item.done .page-thumb-small { border: 1.5px solid #00875A; }
        .page-thumb-small { width: 78px; height: 44px; border-radius: 4px; overflow: hidden; flex-shrink: 0; background: var(--color-bg-subtle); }
        .thumb-placeholder-sm { width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; background: linear-gradient(135deg, var(--color-primary), var(--color-primary-light)); }
        .svg-thumb-wrap { width: 100%; height: 100%; overflow: hidden; position: relative; }
        .svg-thumb-inner { position: absolute; top: 0; left: 0; width: 640px; height: 360px; transform: scale(0.121875); transform-origin: top left; pointer-events: none; }
        .page-meta { flex: 1; display: flex; flex-direction: column; gap: 2px; overflow: hidden; }
        .page-num-label { font-size: 12px; font-weight: 600; color: var(--color-text); }
        .page-part-label { font-size: 11px; color: var(--color-text-muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
        .page-actions { display: flex; gap: 4px; opacity: 0; transition: opacity 0.15s; }
        .page-list-item:hover .page-actions { opacity: 1; }
        .page-action-btn { width: 22px; height: 22px; border-radius: 4px; border: none; background: var(--color-bg-subtle); color: var(--color-text-muted); cursor: pointer; display: flex; align-items: center; justify-content: center; }
        .page-action-btn.danger:hover { background: #FEE2E2; color: #DC2626; }
        .page-action-btn:hover:not(.danger) { background: #DBEAFE; color: var(--color-primary); }
        .empty-pages { text-align: center; padding: 20px; color: var(--color-text-muted); font-size: 13px; display: flex; flex-direction: column; align-items: center; gap: 8px; }
        .preview-panel { flex: 1; display: flex; align-items: center; justify-content: center; background: var(--color-bg-subtle); overflow: auto; padding: 20px; }
        .preview-wrapper { width: 100%; max-width: 860px; display: flex; flex-direction: column; gap: 10px; }
        .preview-label { display: flex; align-items: center; gap: 6px; font-size: 12px; color: var(--color-text-muted); }
        .preview-part { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
        .edit-page-btn { display: flex; align-items: center; gap: 4px; padding: 3px 10px; border-radius: 4px; border: 1px solid var(--color-border); background: white; font-size: 11px; color: var(--color-text-muted); cursor: pointer; margin-left: auto; }
        .edit-page-btn:hover { border-color: var(--color-primary); color: var(--color-primary); }
        .svg-preview { width: 100%; aspect-ratio: 16/9; background: white; border-radius: 8px; box-shadow: var(--shadow-lg); overflow: hidden; }
        .svg-content { width: 100%; height: 100%; }
        .svg-content svg { width: 100%; height: 100%; display: block; }
        .preview-loading, .preview-empty { display: flex; flex-direction: column; align-items: center; gap: 14px; color: var(--color-text-muted); }
        .preview-empty-text { font-size: 15px; font-weight: 500; }
        .spinner { width: 32px; height: 32px; border: 3px solid var(--color-border); border-top-color: var(--color-primary); border-radius: 50%; animation: spin 0.8s linear infinite; }
        .loading-center { display: flex; flex-direction: column; align-items: center; gap: 14px; padding: 80px; color: var(--color-text-muted); }

        /* SettingsModal */
        .settings-modal-box { width: 720px; max-height: 80vh; display: flex; flex-direction: column; }
        .settings-tabs { display: flex; gap: 0; border-bottom: 1px solid var(--color-border); padding: 0 4px; flex-shrink: 0; }
        .settings-tab { display: flex; align-items: center; gap: 6px; padding: 10px 16px; border: none; background: none; cursor: pointer; font-size: 13px; color: var(--color-text-muted); border-bottom: 2px solid transparent; margin-bottom: -1px; transition: all 0.2s; }
        .settings-tab:hover { color: var(--color-text); }
        .settings-tab.active { color: var(--color-primary); border-bottom-color: var(--color-primary); font-weight: 500; }
        .settings-loading { display: flex; flex-direction: column; align-items: center; gap: 12px; padding: 40px; color: var(--color-text-muted); }
        .settings-error { display: flex; align-items: center; gap: 8px; padding: 10px 14px; background: #FEF2F2; border: 1px solid #FECACA; border-radius: 8px; color: #DC2626; font-size: 13px; margin-bottom: 12px; }
        .settings-section { display: flex; flex-direction: column; gap: 16px; }
        .settings-field { display: flex; flex-direction: column; gap: 6px; }
        .settings-field > label { font-size: 13px; font-weight: 500; color: var(--color-text); }
        .field-hint { font-size: 11px; color: var(--color-text-muted); }
        .field-optional { font-size: 11px; color: var(--color-text-muted); font-weight: 400; }
        .provider-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; }
        .provider-btn { display: flex; flex-direction: column; align-items: center; gap: 8px; padding: 16px 12px; border-radius: 10px; border: 2px solid var(--color-border); background: white; cursor: pointer; transition: all 0.2s; font-size: 13px; }
        .provider-btn:hover { border-color: var(--color-primary-light); background: var(--color-bg-subtle); }
        .provider-btn.active { border-color: var(--color-primary); background: #EBF5FF; }
        .provider-icon { font-size: 20px; }
        .provider-name { font-size: 12px; font-weight: 500; color: var(--color-text); }
        .input-group { display: flex; gap: 0; }
        .input-icon-btn { display: flex; align-items: center; justify-content: center; padding: 0 12px; border: 1px solid var(--color-border); border-left: none; background: var(--color-bg-subtle); cursor: pointer; color: var(--color-text-muted); }
        .input-icon-btn:hover { color: var(--color-text); }
        .settings-row { display: flex; gap: 12px; }
        .settings-row .settings-field { flex: 1; }
        .settings-toggle-row { display: flex; align-items: center; justify-content: space-between; gap: 16px; }
        .toggle-label { font-size: 13px; font-weight: 500; color: var(--color-text); }
        .toggle-desc { font-size: 11px; color: var(--color-text-muted); margin-top: 2px; }
        .toggle-switch { position: relative; display: inline-block; width: 40px; height: 22px; }
        .toggle-switch input { opacity: 0; width: 0; height: 0; }
        .toggle-slider { position: absolute; cursor: pointer; inset: 0; background-color: var(--color-border); border-radius: 22px; transition: 0.3s; }
        .toggle-slider::before { position: absolute; content: ''; height: 16px; width: 16px; left: 3px; bottom: 3px; background-color: white; border-radius: 50%; transition: 0.3s; }
        .toggle-switch input:checked + .toggle-slider { background-color: var(--color-primary); }
        .toggle-switch input:checked + .toggle-slider::before { transform: translateX(18px); }
        .test-result { display: flex; align-items: center; gap: 6px; font-size: 12px; padding: 6px 12px; border-radius: 6px; }
        .test-result.ok { background: #F0FDF4; color: #16A34A; border: 1px solid #BBF7D0; }
        .test-result.fail { background: #FEF2F2; color: #DC2626; border: 1px solid #FECACA; }
        .gen-fullscreen-overlay { position: absolute; inset: 0; background: rgba(255,255,255,0.96); z-index: 50; display: flex; align-items: center; justify-content: center; backdrop-filter: blur(4px); }
        .gen-complete-overlay { position: absolute; inset: 0; background: rgba(255,255,255,0.97); z-index: 50; display: flex; align-items: center; justify-content: center; animation: fadeIn 0.3s ease; }
        .gen-complete-card { display: flex; flex-direction: column; align-items: center; gap: 12px; padding: 40px 48px; background: white; border-radius: 12px; box-shadow: var(--shadow-lg); }
        @keyframes fadeIn { from { opacity: 0; transform: scale(0.97); } to { opacity: 1; transform: scale(1); } }
      `}</style>
    </div>
  )
}

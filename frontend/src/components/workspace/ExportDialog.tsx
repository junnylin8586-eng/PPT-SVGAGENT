/**
 * ExportDialog - 导出对话框
 */
import { useState } from 'react'
import { X, Download, CheckSquare, Square, FileText, Loader } from 'lucide-react'
import { api, type Page } from '@/api/client'

interface Props {
  open: boolean
  projectId: string
  projectName: string
  pages: Page[]
  onClose: () => void
}

export default function ExportDialog({ open, projectId, projectName, pages, onClose }: Props) {
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set(pages.map(p => p.page_id)))
  const [exporting, setExporting] = useState(false)
  const [result, setResult] = useState<{ pptx_path: string; size_kb: number; page_count: number } | null>(null)
  const [progress, setProgress] = useState<{ stage: string; progress: number; message: string; total?: number } | null>(null)
  const [error, setError] = useState('')

  if (!open) return null

  const togglePage = (id: string) => {
    const next = new Set(selectedIds)
    if (next.has(id)) next.delete(id)
    else next.add(id)
    setSelectedIds(next)
  }

  const handleExport = async () => {
    if (selectedIds.size === 0) { setError('请至少选择一页'); return }
    setExporting(true)
    setError('')
    setProgress({ stage: 'preparing', progress: 0, message: '正在准备...' })

    try {
      const res = await fetch(`/api/ppt/projects/${projectId}/export`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ page_ids: Array.from(selectedIds) }),
      })

      if (!res.ok) throw new Error(`HTTP ${res.status}`)

      const reader = res.body?.getReader()
      if (!reader) throw new Error('Stream not available')

      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''  // keep incomplete line

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const event = JSON.parse(line.slice(6))
              if (event.type === 'progress') {
                setProgress(event)
              } else if (event.type === 'complete') {
                setResult(event)
                setProgress({ stage: 'done', progress: 100, message: '导出完成！' })
              } else if (event.type === 'error') {
                setError(event.message || '导出失败')
              }
            } catch { /* skip malformed JSON */ }
          }
        }
      }
    } catch (e: any) {
      setError(e.message || '导出失败')
    } finally {
      setExporting(false)
    }
  }

  const handleDownload = () => {
    if (!result?.pptx_path) {
      setError('文件尚未生成，请稍后再试')
      return
    }
    const filename = `${projectName || 'PPT'}.pptx`
    const rawPath = result.pptx_path
    // Encode the filename (last segment) so Chinese chars are safe in URLs
    const segments = rawPath.split('/')
    const encoded = segments.map((s, i) =>
      i === segments.length - 1 ? encodeURIComponent(s) : s
    ).join('/')
    // Direct navigation — works in both dev (vite proxy) and production
    const downloadUrl = `/api/ppt/files/${encoded}?download=1`
    const a = document.createElement('a')
    a.href = downloadUrl
    a.download = filename
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-box" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h2>导出 PPTX</h2>
          <button className="modal-close" onClick={onClose}><X size={20} /></button>
        </div>

        <div className="modal-body">
          {!result ? (
            <>
              {progress && !error && (
                <div className="export-progress">
                  <div className="progress-bar-track">
                    <div
                      className="progress-bar-fill"
                      style={{
                        width: `${progress.progress || 50}%`,
                        transition: 'width 0.5s ease',
                      }}
                    />
                  </div>
                  <p className="progress-message">
                    {exporting ? <Loader size={12} className="spin" /> : null}
                    {progress.message}
                    {progress.total ? ` (${progress.total} 页)` : ''}
                  </p>
                </div>
              )}
              <p className="export-hint">选择要导出的页面（{selectedIds.size} / {pages.length}）</p>
              <div className="page-checklist">
                {pages.map((page, idx) => (
                  <label key={page.page_id} className="page-check-item">
                    <button
                      className="check-btn"
                      onClick={() => togglePage(page.page_id)}
                    >
                      {selectedIds.has(page.page_id)
                        ? <CheckSquare size={18} color="#003371" />
                        : <Square size={18} color="#999" />
                      }
                    </button>
                    <FileText size={15} color="#666" />
                    <span className="check-num">第 {idx + 1} 页</span>
                    <span className="check-part">{page.part || page.outline_content?.slice(0, 16) || ''}</span>
                    <span className={`check-badge ${page.status === 'GENERATED' ? 'gen' : 'pending'}`}>
                      {page.status === 'GENERATED' ? '已生成' : '待生成'}
                    </span>
                  </label>
                ))}
              </div>
              {error && <p className="export-error">{error}</p>}
            </>
          ) : (
            <div className="export-result">
              <div className="result-icon">
                <CheckSquare size={40} color="#00875A" />
              </div>
              <h3>导出成功</h3>
              <p className="result-info">
                {result.size_kb} KB · {selectedIds.size} 页
              </p>
              <p className="result-filename">{projectName || 'PPT'}.pptx</p>
            </div>
          )}
        </div>

        <div className="modal-footer">
          {!result ? (
            <>
              <button className="btn btn-secondary" onClick={onClose}>取消</button>
              <button
                className="btn btn-primary"
                onClick={handleExport}
                disabled={exporting || selectedIds.size === 0}
              >
                {exporting ? <><Loader size={14} className="spin" /> 导出中...</> : <><Download size={14} /> 导出 PPTX</>}
              </button>
            </>
          ) : (
            <>
              <button className="btn btn-secondary" onClick={onClose}>关闭</button>
              <button className="btn btn-green" onClick={handleDownload}>
                <Download size={14} /> 下载文件
              </button>
            </>
          )}
        </div>
      </div>

      <style>{`
        .modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.45); display: flex; align-items: center; justify-content: center; z-index: 1000; backdrop-filter: blur(2px); }
        .modal-box { background: white; border-radius: 12px; width: 500px; max-width: 95vw; box-shadow: 0 20px 60px rgba(0,0,0,0.2); overflow: hidden; }
        .modal-header { display: flex; align-items: center; justify-content: space-between; padding: 18px 24px; border-bottom: 1px solid var(--color-border); }
        .modal-header h2 { font-size: 16px; font-weight: 600; color: var(--color-text); }
        .modal-close { width: 32px; height: 32px; border-radius: 6px; border: none; background: var(--color-bg-subtle); color: var(--color-text-muted); cursor: pointer; display: flex; align-items: center; justify-content: center; }
        .modal-body { padding: 20px 24px; }
        .export-hint { font-size: 13px; color: var(--color-text-muted); margin-bottom: 14px; }
        .page-checklist { display: flex; flex-direction: column; gap: 6px; max-height: 320px; overflow-y: auto; }
        .page-check-item { display: flex; align-items: center; gap: 10px; padding: 10px 12px; border-radius: 8px; cursor: pointer; transition: background 0.15s; }
        .page-check-item:hover { background: var(--color-bg-subtle); }
        .check-btn { background: none; border: none; cursor: pointer; padding: 0; display: flex; }
        .check-num { font-size: 13px; font-weight: 600; color: var(--color-text); width: 60px; }
        .check-part { font-size: 12px; color: var(--color-text-muted); flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
        .check-badge { font-size: 11px; padding: 2px 8px; border-radius: 10px; font-weight: 500; }
        .check-badge.gen { background: #D1FAE5; color: #065F46; }
        .check-badge.pending { background: #FEF3C7; color: #92400E; }
        .export-error { color: #DC2626; font-size: 13px; margin-top: 10px; }
        .export-progress { margin-bottom: 14px; }
        .progress-bar-track { width: 100%; height: 6px; background: #E5E7EB; border-radius: 3px; overflow: hidden; margin-bottom: 6px; }
        .progress-bar-fill { height: 100%; background: var(--color-primary); border-radius: 3px; min-width: 4px; }
        .progress-message { font-size: 12px; color: var(--color-text-muted); display: flex; align-items: center; gap: 6px; }
        .export-result { display: flex; flex-direction: column; align-items: center; gap: 10px; padding: 20px 0; text-align: center; }
        .result-icon { width: 72px; height: 72px; background: #D1FAE5; border-radius: 50%; display: flex; align-items: center; justify-content: center; }
        .export-result h3 { font-size: 18px; font-weight: 600; color: var(--color-text); }
        .result-info { font-size: 14px; color: var(--color-text-muted); }
        .result-filename { font-size: 13px; color: var(--color-text-muted); background: var(--color-bg-subtle); padding: 4px 12px; border-radius: 6px; font-family: monospace; }
        .modal-footer { display: flex; justify-content: flex-end; gap: 10px; padding: 14px 24px; border-top: 1px solid var(--color-border); background: var(--color-bg-subtle); }
        .btn { display: inline-flex; align-items: center; gap: 6px; padding: 8px 18px; border-radius: 6px; font-size: 14px; font-weight: 500; cursor: pointer; transition: all 0.2s; border: none; }
        .btn-secondary { background: white; color: var(--color-text); border: 1px solid var(--color-border); }
        .btn-secondary:hover { background: var(--color-bg-subtle); }
        .btn-primary { background: var(--color-primary); color: white; }
        .btn-primary:hover { background: var(--color-primary-light); }
        .btn-primary:disabled { opacity: 0.6; cursor: not-allowed; }
        .btn-green { background: #00875A; color: white; }
        .btn-green:hover { background: #006B47; }
        .spin { animation: spin 1s linear infinite; }
        @keyframes spin { to { transform: rotate(360deg); } }
      `}</style>
    </div>
  )
}
/**
 * GenerationProgress - 生成进度组件
 * 显示每个页面的生成状态
 */
import { CheckCircle, Loader, AlertCircle } from 'lucide-react'
import type { Page } from '@/api/client'

interface Props {
  pages: Page[]
  currentIndex: number  // 当前正在生成的页索引（-1 表示全部完成）
  status: 'idle' | 'generating' | 'completed' | 'error'
  error?: string
}

const STATUS_CONFIG = {
  DRAFT: { label: '待生成', color: '#999', icon: null },
  PENDING: { label: '等待中', color: '#E07B39', icon: null },
  GENERATING: { label: '生成中', color: '#003371', icon: Loader },
  GENERATED: { label: '已完成', color: '#00875A', icon: CheckCircle },
  FAILED: { label: '失败', color: '#DC2626', icon: AlertCircle },
}

export default function GenerationProgress({ pages, currentIndex, status, error }: Props) {
  if (status === 'idle') return null

  return (
    <div className="gen-progress">
      <div className="gen-header">
        {status === 'generating' && (
          <div className="gen-status">
            <Loader size={16} className="spin-icon" color="#003371" />
            <span>AI 正在生成第 {currentIndex + 1} / {pages.length} 页...</span>
          </div>
        )}
        {status === 'completed' && (
          <div className="gen-status done">
            <CheckCircle size={16} color="#00875A" />
            <span>生成完成 · {pages.length} 页</span>
          </div>
        )}
        {status === 'error' && (
          <div className="gen-status err">
            <AlertCircle size={16} color="#DC2626" />
            <span>{error || '生成失败'}</span>
          </div>
        )}
      </div>

      <div className="gen-pages">
        {pages.map((page, idx) => {
          const cfg = STATUS_CONFIG[page.status as keyof typeof STATUS_CONFIG] || STATUS_CONFIG.DRAFT
          const isActive = idx === currentIndex
          return (
            <div key={page.page_id} className={`gen-page-item ${isActive ? 'active' : ''} ${page.status === 'GENERATED' ? 'done' : ''}`}>
              <div className="gen-page-dot" style={{ background: cfg.color }}>
                {cfg.icon && <cfg.icon size={10} className={isActive ? 'spin-icon' : ''} color="white" />}
              </div>
              <span className="gen-page-label">第 {idx + 1} 页</span>
              <span className="gen-page-part">{page.part || page.outline_content?.slice(0, 12) || ''}</span>
            </div>
          )
        })}
      </div>

      <style>{`
        .gen-progress {
          background: white;
          border-radius: 10px;
          padding: 16px 20px;
          box-shadow: var(--shadow-md);
          border: 1px solid var(--color-border);
        }
        .gen-header { margin-bottom: 14px; }
        .gen-status {
          display: flex; align-items: center; gap: 8px;
          font-size: 14px; font-weight: 500; color: var(--color-text);
        }
        .gen-status.done { color: #00875A; }
        .gen-status.err { color: #DC2626; }
        .spin-icon { animation: spin 1s linear infinite; }
        @keyframes spin { to { transform: rotate(360deg); } }
        .gen-pages { display: flex; flex-direction: column; gap: 8px; }
        .gen-page-item {
          display: flex; align-items: center; gap: 10px;
          padding: 8px 12px; border-radius: 6px;
          background: var(--color-bg-subtle);
          transition: all 0.2s;
        }
        .gen-page-item.active { background: #EBF5FF; border: 1px solid #BFDBFE; }
        .gen-page-item.done { background: #F0FDF4; }
        .gen-page-dot {
          width: 20px; height: 20px; border-radius: 50%;
          display: flex; align-items: center; justify-content: center;
          flex-shrink: 0;
        }
        .gen-page-label { font-size: 12px; font-weight: 600; color: var(--color-text); width: 60px; }
        .gen-page-part { font-size: 12px; color: var(--color-text-muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
      `}</style>
    </div>
  )
}
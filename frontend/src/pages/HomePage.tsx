import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Plus, Clock, Trash2, FolderOpen, FileText, Sparkles } from 'lucide-react'
import { useProjectStore } from '@/store/projectStore'
import NewProjectModal from '@/components/home/NewProjectModal'

function formatDate(iso: string) {
  const d = new Date(iso)
  const now = new Date()
  const diff = now.getTime() - d.getTime()
  if (diff < 60000) return '刚刚'
  if (diff < 3600000) return `${Math.floor(diff / 60000)} 分钟前`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)} 小时前`
  return d.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}

export default function HomePage() {
  const navigate = useNavigate()
  const { projects, fetchProjects, deleteProject, loading } = useProjectStore()
  const [showNewModal, setShowNewModal] = useState(false)

  useEffect(() => {
    fetchProjects()
  }, [])

  return (
    <div className="home-page">
      {/* Hero */}
      <div className="hero-banner">
        <div className="hero-content">
          <div className="hero-icon">
            <Sparkles size={28} color="white" />
          </div>
          <div>
            <h1 className="hero-title">AI 智能 PPT 生成</h1>
            <p className="hero-sub">输入想法，AI 自动生成专业演示文稿 · 支持矢量可编辑导出</p>
          </div>
        </div>
        <button className="btn btn-hero" onClick={() => setShowNewModal(true)}>
          <Plus size={18} />
          创建新项目
        </button>
      </div>

      {/* Quick Actions */}
      <div className="quick-actions">
        <div className="section-header">
          <h2 className="section-title">最近项目</h2>
          <span className="section-count">{projects.length} 个项目</span>
        </div>
      </div>

      {/* Project Grid */}
      {loading ? (
        <div className="loading-state">
          <div className="spinner" />
          <p>加载中...</p>
        </div>
      ) : projects.length === 0 ? (
        <div className="empty-state">
          <FolderOpen size={48} color="#CBD5E1" />
          <p>暂无项目</p>
          <button className="btn btn-primary" onClick={() => setShowNewModal(true)}>
            <Plus size={16} /> 创建第一个项目
          </button>
        </div>
      ) : (
        <div className="project-grid">
          {projects.map(project => (
            <div
              key={project.project_id}
              className="project-card card"
              onClick={() => navigate(`/workspace/${project.project_id}`)}
            >
              <div className="project-card-header">
                <div className="project-icon">
                  <FileText size={20} color="var(--color-primary)" />
                </div>
                <button
                  className="delete-btn"
                  onClick={e => {
                    e.stopPropagation()
                    if (confirm('确定删除该项目？')) deleteProject(project.project_id)
                  }}
                >
                  <Trash2 size={14} />
                </button>
              </div>

              <h3 className="project-name">{project.name || '未命名项目'}</h3>
              <p className="project-type">{project.creation_type === 'idea' ? 'AI 生成' : project.creation_type === 'outline' ? '大纲生成' : '描述生成'}</p>

              <div className="project-footer">
                <span className={`badge ${
                  project.status === 'completed' ? 'badge-green' :
                  project.status === 'generating' ? 'badge-blue' :
                  project.status === 'failed' ? 'badge-red' : 'badge-gray'
                }`}>
                  {project.status === 'draft' ? '草稿' :
                   project.status === 'generating' ? '生成中' :
                   project.status === 'completed' ? '完成' :
                   project.status === 'failed' ? '失败' : project.status}
                </span>
                <span className="project-time">
                  <Clock size={12} />
                  {formatDate(project.updated_at || project.created_at)}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}

      {showNewModal && <NewProjectModal onClose={() => setShowNewModal(false)} />}

      <style>{`
        .home-page {
          max-width: 1200px;
          margin: 0 auto;
          padding: 32px 24px;
        }
        .hero-banner {
          display: flex;
          align-items: center;
          justify-content: space-between;
          background: linear-gradient(135deg, var(--color-primary) 0%, var(--color-primary-light) 100%);
          border-radius: 12px;
          padding: 28px 32px;
          margin-bottom: 32px;
          box-shadow: var(--shadow-lg);
        }
        .hero-content {
          display: flex;
          align-items: center;
          gap: 16px;
        }
        .hero-icon {
          width: 52px;
          height: 52px;
          background: rgba(255,255,255,0.18);
          border-radius: 12px;
          display: flex;
          align-items: center;
          justify-content: center;
        }
        .hero-title {
          font-size: 22px;
          font-weight: 700;
          color: white;
          margin-bottom: 4px;
        }
        .hero-sub {
          font-size: 14px;
          color: rgba(255,255,255,0.78);
        }
        .btn-hero {
          background: white;
          color: var(--color-primary);
          padding: 10px 22px;
          font-size: 15px;
          font-weight: 600;
          border-radius: 8px;
          box-shadow: 0 4px 12px rgba(0,51,113,0.25);
        }
        .btn-hero:hover {
          background: rgba(255,255,255,0.92);
          transform: translateY(-1px);
        }
        .quick-actions {
          margin-bottom: 20px;
        }
        .section-header {
          display: flex;
          align-items: center;
          gap: 12px;
        }
        .section-title {
          font-size: 16px;
          font-weight: 600;
          color: var(--color-text);
        }
        .section-count {
          font-size: 13px;
          color: var(--color-text-muted);
          background: var(--color-bg-subtle);
          padding: 2px 10px;
          border-radius: 12px;
        }
        .loading-state, .empty-state {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          gap: 16px;
          padding: 64px;
          color: var(--color-text-muted);
        }
        .spinner {
          width: 36px;
          height: 36px;
          border: 3px solid var(--color-border);
          border-top-color: var(--color-primary);
          border-radius: 50%;
          animation: spin 0.8s linear infinite;
        }
        @keyframes spin { to { transform: rotate(360deg); } }
        .project-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
          gap: 16px;
        }
        .project-card {
          padding: 20px;
          cursor: pointer;
          transition: all 0.2s;
        }
        .project-card:hover {
          transform: translateY(-2px);
          box-shadow: var(--shadow-lg);
        }
        .project-card-header {
          display: flex;
          align-items: flex-start;
          justify-content: space-between;
          margin-bottom: 14px;
        }
        .project-icon {
          width: 40px;
          height: 40px;
          background: var(--color-bg-subtle);
          border-radius: 8px;
          display: flex;
          align-items: center;
          justify-content: center;
        }
        .delete-btn {
          width: 28px;
          height: 28px;
          border-radius: 6px;
          border: none;
          background: transparent;
          color: var(--color-text-light);
          cursor: pointer;
          display: flex;
          align-items: center;
          justify-content: center;
          opacity: 0;
          transition: all 0.2s;
        }
        .project-card:hover .delete-btn {
          opacity: 1;
        }
        .delete-btn:hover {
          background: #FEE2E2;
          color: #DC2626;
        }
        .project-name {
          font-size: 15px;
          font-weight: 600;
          color: var(--color-text);
          margin-bottom: 4px;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }
        .project-type {
          font-size: 12px;
          color: var(--color-text-muted);
          margin-bottom: 14px;
        }
        .project-footer {
          display: flex;
          align-items: center;
          justify-content: space-between;
        }
        .badge {
          padding: 3px 10px;
          border-radius: 12px;
          font-size: 11px;
          font-weight: 600;
        }
        .badge-blue { background: #DBEAFE; color: #1D4ED8; }
        .badge-green { background: #D1FAE5; color: #065F46; }
        .badge-gray { background: var(--color-bg-subtle); color: var(--color-text-muted); }
        .badge-red { background: #FEE2E2; color: #DC2626; }
        .project-time {
          display: flex;
          align-items: center;
          gap: 4px;
          font-size: 12px;
          color: var(--color-text-light);
        }
      `}</style>
    </div>
  )
}

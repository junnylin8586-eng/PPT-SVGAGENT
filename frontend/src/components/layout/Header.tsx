import { Link, useLocation } from 'react-router-dom'
import { Layers, Plus, FolderOpen, History } from 'lucide-react'

interface HeaderProps {
  onNewProject?: () => void
}

export default function Header({ onNewProject }: HeaderProps) {
  const location = useLocation()

  const navItems = [
    { path: '/', label: '首页', icon: Layers },
    { path: '/templates', label: '模板库', icon: FolderOpen },
    { path: '/history', label: '历史', icon: History },
  ]

  return (
    <header className="header">
      <div className="header-left">
        {/* Logo */}
        <div className="logo">
          <div className="logo-icon">
            <Layers size={22} color="white" strokeWidth={2.5} />
          </div>
          <span className="logo-text">PPT Agent</span>
        </div>

        {/* Nav */}
        <nav className="header-nav">
          {navItems.map(item => (
            <Link
              key={item.path}
              to={item.path}
              className={`nav-item ${location.pathname === item.path ? 'active' : ''}`}
            >
              <item.icon size={16} />
              {item.label}
            </Link>
          ))}
        </nav>
      </div>

      <div className="header-right">
        <button className="btn btn-primary" onClick={onNewProject}>
          <Plus size={16} />
          新建项目
        </button>
      </div>

      <style>{`
        .header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          height: 56px;
          padding: 0 24px;
          background: var(--color-primary);
          box-shadow: 0 2px 8px rgba(0,51,113,0.15);
          position: sticky;
          top: 0;
          z-index: 100;
        }
        .header-left {
          display: flex;
          align-items: center;
          gap: 32px;
        }
        .logo {
          display: flex;
          align-items: center;
          gap: 10px;
        }
        .logo-icon {
          width: 34px;
          height: 34px;
          background: rgba(255,255,255,0.15);
          border-radius: 8px;
          display: flex;
          align-items: center;
          justify-content: center;
        }
        .logo-text {
          font-size: 17px;
          font-weight: 700;
          color: white;
          letter-spacing: 0.3px;
        }
        .header-nav {
          display: flex;
          align-items: center;
          gap: 4px;
        }
        .nav-item {
          display: flex;
          align-items: center;
          gap: 6px;
          padding: 6px 14px;
          border-radius: 6px;
          color: rgba(255,255,255,0.75);
          text-decoration: none;
          font-size: 14px;
          font-weight: 500;
          transition: all 0.2s;
        }
        .nav-item:hover {
          background: rgba(255,255,255,0.12);
          color: white;
        }
        .nav-item.active {
          background: rgba(255,255,255,0.2);
          color: white;
        }
        .header-right {
          display: flex;
          align-items: center;
          gap: 12px;
        }
        .btn-primary {
          background: rgba(255,255,255,0.18);
          color: white;
          border: 1px solid rgba(255,255,255,0.3);
          padding: 7px 16px;
          font-size: 13px;
        }
        .btn-primary:hover {
          background: rgba(255,255,255,0.28);
        }
      `}</style>
    </header>
  )
}

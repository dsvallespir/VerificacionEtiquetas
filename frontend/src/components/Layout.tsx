import { type ReactNode } from 'react'
import { Link, useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { LayoutDashboard, FolderOpen, LogOut, Tag } from 'lucide-react'
import clsx from 'clsx'

const NAV = [
  { label: 'Dashboard', href: '/', icon: LayoutDashboard },
  { label: 'Proyectos', href: '/projects', icon: FolderOpen },
]

export function Layout({ children }: { children: ReactNode }) {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <div className="flex min-h-screen">
      {/* Sidebar */}
      <aside className="w-64 bg-slate-900 text-white flex flex-col">
        <div className="px-6 py-5 border-b border-slate-700 flex items-center gap-2">
          <Tag className="w-6 h-6 text-brand-500" />
          <span className="font-bold text-lg">VerifEtiquetas</span>
        </div>

        <nav className="flex-1 px-3 py-4 space-y-1">
          {NAV.map((item) => {
            const active = location.pathname === item.href ||
              (item.href !== '/' && location.pathname.startsWith(item.href))
            return (
              <Link
                key={item.href}
                to={item.href}
                className={clsx(
                  'flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors',
                  active
                    ? 'bg-brand-600 text-white'
                    : 'text-slate-300 hover:bg-slate-800 hover:text-white',
                )}
              >
                <item.icon className="w-4 h-4" />
                {item.label}
              </Link>
            )
          })}
        </nav>

        <div className="px-4 py-4 border-t border-slate-700">
          <div className="text-xs text-slate-400 mb-2">{user?.full_name || user?.username}</div>
          <button
            onClick={handleLogout}
            className="flex items-center gap-2 text-sm text-slate-300 hover:text-white transition-colors"
          >
            <LogOut className="w-4 h-4" />
            Cerrar sesión
          </button>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-auto bg-slate-50">
        {children}
      </main>
    </div>
  )
}

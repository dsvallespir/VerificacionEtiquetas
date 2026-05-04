import { useEffect, useState } from 'react'
import { formatDate } from '../utils/date'
import { Link } from 'react-router-dom'
import { projectsApi } from '../api/endpoints'
import type { Project } from '../types'
import { StatusBadge } from '../components/StatusBadge'
import { useAuth } from '../context/AuthContext'
import {
  FolderOpen, Plus, CheckCircle2, Clock, AlertTriangle, XCircle
} from 'lucide-react'

const STAT_ICONS = {
  total: FolderOpen,
  verified: CheckCircle2,
  in_review: Clock,
  rejected: XCircle,
}

export default function DashboardPage() {
  const { user } = useAuth()
  const [projects, setProjects] = useState<Project[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    projectsApi.list().then(setProjects).finally(() => setLoading(false))
  }, [])

  const stats = {
    total: projects.length,
    verified: projects.filter((p) => p.status === 'VERIFICADA').length,
    in_review: projects.filter(
      (p) => p.status === 'EN_REVISION_REDISENO' || p.status === 'EN_REVISION_IMPRENTA',
    ).length,
    rejected: projects.filter((p) => p.status === 'RECHAZADA').length,
  }

  const recent = [...projects].sort(
    (a, b) => new Date(b.updated_at ? b.updated_at + (!b.updated_at.includes('Z') && !b.updated_at.includes('+') ? 'Z' : '') : 0).getTime() - new Date(a.updated_at ? a.updated_at + (!a.updated_at.includes('Z') && !a.updated_at.includes('+') ? 'Z' : '') : 0).getTime()
  ).slice(0, 5)

  return (
    <div className="p-8">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-slate-900">
          Bienvenido, {user?.full_name || user?.username}
        </h1>
        <p className="text-slate-500 mt-1">Panel de control de verificación de etiquetas</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        {(
          [
            { key: 'total', label: 'Total proyectos', color: 'text-slate-700', bg: 'bg-slate-100' },
            { key: 'verified', label: 'Verificadas', color: 'text-green-700', bg: 'bg-green-100' },
            { key: 'in_review', label: 'En revisión', color: 'text-yellow-700', bg: 'bg-yellow-100' },
            { key: 'rejected', label: 'Rechazadas', color: 'text-red-700', bg: 'bg-red-100' },
          ] as const
        ).map(({ key, label, color, bg }) => {
          const Icon = STAT_ICONS[key]
          return (
            <div key={key} className="bg-white rounded-xl border border-slate-200 p-5">
              <div className="flex items-center justify-between mb-3">
                <div className={`${bg} p-2 rounded-lg`}>
                  <Icon className={`w-5 h-5 ${color}`} />
                </div>
              </div>
              <div className="text-3xl font-bold text-slate-900">{stats[key]}</div>
              <div className="text-sm text-slate-500 mt-1">{label}</div>
            </div>
          )
        })}
      </div>

      {/* Recent projects */}
      <div className="bg-white rounded-xl border border-slate-200">
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100">
          <h2 className="font-semibold text-slate-900">Proyectos recientes</h2>
          <Link
            to="/projects/new"
            className="flex items-center gap-1 text-sm bg-brand-600 text-white px-3 py-1.5 rounded-lg hover:bg-brand-700 transition-colors"
          >
            <Plus className="w-4 h-4" />
            Nuevo proyecto
          </Link>
        </div>

        {loading ? (
          <div className="p-8 text-center text-slate-500">Cargando...</div>
        ) : recent.length === 0 ? (
          <div className="p-12 text-center">
            <AlertTriangle className="w-10 h-10 text-slate-300 mx-auto mb-3" />
            <p className="text-slate-500">No hay proyectos aún.</p>
            <Link
              to="/projects/new"
              className="mt-4 inline-block text-sm text-brand-600 hover:underline"
            >
              Crear el primero
            </Link>
          </div>
        ) : (
          <div className="divide-y divide-slate-100">
            {recent.map((project) => (
              <Link
                key={project.id}
                to={`/projects/${project.id}`}
                className="flex items-center justify-between px-6 py-4 hover:bg-slate-50 transition-colors"
              >
                <div>
                  <div className="font-medium text-slate-900">{project.name}</div>
                  <div className="text-sm text-slate-500">
                    {project.product_name || 'Sin producto'} ·{' '}
                    {formatDate(project.updated_at)}
                  </div>
                </div>
                <StatusBadge status={project.status} />
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

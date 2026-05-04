import { useEffect, useState } from 'react'
import { formatDate } from '../utils/date'
import { Link } from 'react-router-dom'
import { projectsApi } from '../api/endpoints'
import type { Project } from '../types'
import { StatusBadge } from '../components/StatusBadge'
import { Plus, Search } from 'lucide-react'

export default function ProjectsPage() {
  const [projects, setProjects] = useState<Project[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')

  useEffect(() => {
    projectsApi.list().then(setProjects).finally(() => setLoading(false))
  }, [])

  const filtered = projects.filter(
    (p) =>
      p.name.toLowerCase().includes(search.toLowerCase()) ||
      (p.product_name?.toLowerCase() ?? '').includes(search.toLowerCase()),
  )

  return (
    <div className="p-8">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-slate-900">Proyectos</h1>
        <Link
          to="/projects/new"
          className="flex items-center gap-2 bg-brand-600 text-white px-4 py-2 rounded-lg hover:bg-brand-700 transition-colors text-sm font-medium"
        >
          <Plus className="w-4 h-4" />
          Nuevo proyecto
        </Link>
      </div>

      <div className="relative mb-6">
        <Search className="absolute left-3 top-2.5 w-4 h-4 text-slate-400" />
        <input
          type="text"
          placeholder="Buscar por nombre o producto..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full pl-9 pr-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500 text-sm"
        />
      </div>

      {loading ? (
        <div className="text-center text-slate-500 py-12">Cargando proyectos...</div>
      ) : filtered.length === 0 ? (
        <div className="text-center text-slate-500 py-12">
          {search ? 'Sin resultados para la búsqueda.' : 'No hay proyectos creados aún.'}
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {filtered.map((project) => (
            <Link
              key={project.id}
              to={`/projects/${project.id}`}
              className="bg-white border border-slate-200 rounded-xl p-5 hover:shadow-md transition-shadow"
            >
              <div className="flex items-start justify-between mb-3">
                <div>
                  <h3 className="font-semibold text-slate-900">{project.name}</h3>
                  {project.product_name && (
                    <p className="text-sm text-slate-500">{project.product_name}</p>
                  )}
                </div>
                <StatusBadge status={project.status} />
              </div>
              {project.description && (
                <p className="text-sm text-slate-600 line-clamp-2 mb-3">{project.description}</p>
              )}
              <p className="text-xs text-slate-400">
                Actualizado: {formatDate(project.updated_at)}
              </p>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}

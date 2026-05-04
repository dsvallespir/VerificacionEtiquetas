import { useEffect, useState } from 'react'
import { formatDate } from '../utils/date'
import { useParams, Link } from 'react-router-dom'
import { reportsApi } from '../api/endpoints'
import type { Report } from '../types'
import ReactMarkdown from 'react-markdown'
import { ArrowLeft, FileText } from 'lucide-react'

export default function ReportsPage() {
  const { projectId } = useParams<{ projectId: string }>()
  const [reports, setReports] = useState<Report[]>([])
  const [selected, setSelected] = useState<Report | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!projectId) return
    reportsApi.list(Number(projectId)).then(setReports).finally(() => setLoading(false))
  }, [projectId])

  return (
    <div className="p-8">
      <div className="flex items-center gap-3 mb-6">
        <Link to={`/projects/${projectId}`} className="text-slate-400 hover:text-slate-600">
          <ArrowLeft className="w-5 h-5" />
        </Link>
        <h1 className="text-2xl font-bold text-slate-900">Reportes del proyecto</h1>
      </div>

      {loading ? (
        <p className="text-slate-500">Cargando reportes...</p>
      ) : reports.length === 0 ? (
        <div className="text-center py-12 text-slate-500">
          <FileText className="w-10 h-10 mx-auto mb-3 text-slate-300" />
          <p>No hay reportes generados para este proyecto.</p>
        </div>
      ) : (
        <div className="grid md:grid-cols-3 gap-6">
          {/* Lista */}
          <div className="space-y-2">
            {reports.map((r) => (
              <button
                key={r.id}
                onClick={() => setSelected(r)}
                className={`w-full text-left p-4 rounded-xl border transition-colors ${
                  selected?.id === r.id
                    ? 'border-brand-500 bg-brand-50'
                    : 'border-slate-200 hover:border-brand-300'
                }`}
              >
                <p className="font-medium text-sm text-slate-900 line-clamp-2">{r.title}</p>
                <p className="text-xs text-slate-500 mt-1">
                  {formatDate(r.generated_at)}
                </p>
              </button>
            ))}
          </div>

          {/* Detalle */}
          <div className="md:col-span-2 bg-white border border-slate-200 rounded-xl p-6 overflow-auto max-h-[70vh]">
            {selected ? (
              <div className="prose prose-slate prose-sm max-w-none">
                <ReactMarkdown>{selected.content || ''}</ReactMarkdown>
              </div>
            ) : (
              <p className="text-slate-400 text-sm">Seleccioná un reporte para verlo.</p>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

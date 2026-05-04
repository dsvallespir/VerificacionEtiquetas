import { useEffect, useState, useCallback } from 'react'
import { useParams, Link } from 'react-router-dom'
import { projectsApi, labelsApi, reportsApi } from '../api/endpoints'
import type { Project, LabelVersion, Comparison } from '../types'
import { StatusBadge } from '../components/StatusBadge'
import { toast } from 'react-hot-toast'
import {
  ArrowLeft, Upload, RefreshCw, CheckCircle, XCircle,
  FileText, ChevronRight, Eye, AlertTriangle
} from 'lucide-react'
import { useDropzone } from 'react-dropzone'
import { formatDateTime } from '../utils/date'

const STEP_LABELS: Record<string, string> = {
  DISENO: 'Paso 1 – Diseño base',
  REDISENO: 'Paso 2 – Rediseño',
  MUESTRA_IMPRENTA: 'Paso 3 – Muestra de Imprenta',
}

const STEP_ORDER = ['DISENO', 'REDISENO', 'MUESTRA_IMPRENTA']

function UploadCard({
  step,
  existing,
  onUploaded,
  onReplaced,
  projectId,
}: {
  step: string
  existing: LabelVersion | undefined
  onUploaded: () => void
  onReplaced: () => void
  projectId: number
}) {
  const [loading, setLoading] = useState(false)
  const [notes, setNotes] = useState('')
  const [replacing, setReplacing] = useState(false)
  const [showLightbox, setShowLightbox] = useState(false)

  const onDrop = useCallback(
    async (acceptedFiles: File[]) => {
      if (!acceptedFiles[0]) return
      setLoading(true)
      try {
        await labelsApi.upload(projectId, step, acceptedFiles[0], notes || undefined)
        toast.success(`${STEP_LABELS[step]} cargado correctamente`)
        setReplacing(false)
        if (existing) onReplaced()
        onUploaded()
      } catch (err: unknown) {
        const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
        toast.error(msg || 'Error al cargar imagen')
      } finally {
        setLoading(false)
      }
    },
    [projectId, step, notes, onUploaded],
  )

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'image/*': [], 'application/pdf': ['.pdf'] },
    maxFiles: 1,
    disabled: loading,
  })

  // Vista: imagen existente y no en modo reemplazo
  if (existing && !replacing) {
    return (
      <>
        <div className="border border-green-200 bg-green-50 rounded-xl p-4 flex-1">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2 text-green-700">
              <CheckCircle className="w-4 h-4" />
              <span className="text-sm font-medium">{STEP_LABELS[step]}</span>
            </div>
            <button
              onClick={() => setReplacing(true)}
              className="flex items-center gap-1 text-xs text-slate-500 hover:text-brand-600 border border-slate-200 bg-white rounded-lg px-2 py-1 transition-colors"
              title="Reemplazar imagen"
            >
              <RefreshCw className="w-3 h-3" />
              Reemplazar
            </button>
          </div>
          <img
            src={labelsApi.staticUrl(existing.image_path)}
            alt={step}
            onClick={() => setShowLightbox(true)}
            className="w-full max-h-48 object-contain rounded-lg bg-white border border-green-200 cursor-zoom-in"
          />
          {existing.notes && (
            <p className="text-xs text-slate-500 mt-2">{existing.notes}</p>
          )}
          <p className="text-xs text-slate-400 mt-1">
            {existing.uploader ? `${existing.uploader.username} · ` : ''}{formatDateTime(existing.uploaded_at)}
          </p>
        </div>

        {/* Lightbox */}
        {showLightbox && (
          <div
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4"
            onClick={() => setShowLightbox(false)}
          >
            <div
              className="relative max-w-[95vw] max-h-[95vh] flex flex-col items-center"
              onClick={e => e.stopPropagation()}
            >
              <div className="flex items-center justify-between w-full mb-2">
                <span className="text-white text-sm font-medium">{STEP_LABELS[step]}</span>
                <button
                  onClick={() => setShowLightbox(false)}
                  className="text-white hover:text-slate-300 text-2xl leading-none ml-4"
                  title="Cerrar"
                >
                  &times;
                </button>
              </div>
              <img
                src={labelsApi.staticUrl(existing.image_path)}
                alt={step}
                className="max-w-full max-h-[85vh] object-contain rounded-lg shadow-2xl"
              />
            </div>
          </div>
        )}
      </>
    )
  }

  // Vista: zona de carga (nuevo o reemplazo)
  return (
    <div className="border border-slate-200 rounded-xl p-4 flex-1">
      <div className="flex items-center justify-between mb-3">
        <p className="text-sm font-medium text-slate-700">{STEP_LABELS[step]}</p>
        {replacing && (
          <div className="flex items-center gap-1 text-xs text-amber-600 bg-amber-50 border border-amber-200 rounded-lg px-2 py-1">
            <AlertTriangle className="w-3 h-3" />
            Se reiniciará la verificación
          </div>
        )}
      </div>
      <input
        type="text"
        placeholder="Notas (opcional)"
        value={notes}
        onChange={(e) => setNotes(e.target.value)}
        className="w-full text-sm border border-slate-200 rounded-lg px-3 py-1.5 mb-3 focus:outline-none focus:ring-1 focus:ring-brand-500"
      />
      <div
        {...getRootProps()}
        className={`border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition-colors ${
          isDragActive ? 'border-brand-500 bg-brand-50' : 'border-slate-300 hover:border-brand-400'
        } ${loading ? 'opacity-50 pointer-events-none' : ''}`}
      >
        <input {...getInputProps()} />
        <Upload className="w-6 h-6 text-slate-400 mx-auto mb-2" />
        <p className="text-sm text-slate-500">
          {loading ? 'Subiendo...' : isDragActive ? 'Soltar aquí' : 'Arrastrá o hacé clic para subir'}
        </p>
        <p className="text-xs text-slate-400 mt-1">Imagen o PDF (se extrae la primera página)</p>
      </div>
      {replacing && (
        <button
          onClick={() => setReplacing(false)}
          className="mt-2 text-xs text-slate-400 hover:text-slate-600 w-full text-center"
        >
          Cancelar
        </button>
      )}
    </div>
  )
}

export default function ProjectDetailPage() {
  const { id } = useParams<{ id: string }>()
  const projectId = Number(id)
  const [project, setProject] = useState<Project | null>(null)
  const [versions, setVersions] = useState<LabelVersion[]>([])
  const [activeComparison, setActiveComparison] = useState<Comparison | null>(null)
  const [comparing, setComparing] = useState(false)
  const [reviewLoading, setReviewLoading] = useState(false)
  const [reviewNotes, setReviewNotes] = useState('')

  const reload = useCallback(async () => {
    const [proj, vers] = await Promise.all([
      projectsApi.get(projectId),
      labelsApi.listVersions(projectId),
    ])
    setProject(proj)
    setVersions(vers)
  }, [projectId])

  useEffect(() => {
    reload()
  }, [reload])

  const versionByStep = (step: string) => versions.find((v) => v.step === step)

  const handleCompare = async (revisedStep: string) => {
    const revised = versionByStep(revisedStep)
    if (!revised) return
    setComparing(true)
    try {
      const comp = await labelsApi.compare(projectId, revised.id)
      setActiveComparison(comp)
      await reload()   // actualiza versions con annotated_image_path
      toast.success('Comparación completada')
    } catch {
      toast.error('Error al comparar etiquetas')
    } finally {
      setComparing(false)
    }
  }

  const handleReview = async (status: 'APROBADO' | 'RECHAZADO') => {
    if (!activeComparison) return
    setReviewLoading(true)
    try {
      await labelsApi.reviewComparison(activeComparison.id, status, reviewNotes || undefined)
      toast.success(status === 'APROBADO' ? 'Aprobado ✓' : 'Rechazado')
      setActiveComparison(null)
      reload()
    } catch {
      toast.error('Error al guardar revisión')
    } finally {
      setReviewLoading(false)
    }
  }

  const handleGenerateReport = async () => {
    if (!activeComparison) return
    try {
      const report = await reportsApi.generate(projectId, activeComparison.id)
      toast.success('Reporte generado')
      console.log(report)
    } catch {
      toast.error('Error al generar reporte')
    }
  }

  if (!project) {
    return <div className="p-8 text-slate-500">Cargando...</div>
  }

  const baseVersion = versionByStep('DISENO')
  const revisableSteps = ['REDISENO', 'MUESTRA_IMPRENTA'].filter((s) => versionByStep(s))

  return (
    <div className="p-8">
      <div className="flex items-center gap-3 mb-6">
        <Link to="/projects" className="text-slate-400 hover:text-slate-600">
          <ArrowLeft className="w-5 h-5" />
        </Link>
        <div className="flex-1">
          <h1 className="text-2xl font-bold text-slate-900">{project.name}</h1>
          {project.product_name && (
            <p className="text-sm text-slate-500">{project.product_name}</p>
          )}
        </div>
        <StatusBadge status={project.status} />
      </div>

      {/* Flujo de etiquetas */}
      <div className="mb-8">
        <h2 className="text-sm font-semibold text-slate-500 uppercase tracking-wide mb-4">
          Etiquetas del proyecto
        </h2>
        <div className="grid md:grid-cols-3 gap-4 items-start">
          {STEP_ORDER.map((step, i) => (
            <div key={step} className="flex items-start gap-2">
              <UploadCard
                step={step}
                existing={versionByStep(step)}
                onUploaded={reload}
                onReplaced={() => setActiveComparison(null)}
                projectId={projectId}
              />
              {i < 2 && (
                <ChevronRight className="w-5 h-5 text-slate-300 mt-14 flex-shrink-0 hidden md:block" />
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Comparaciones */}
      {baseVersion && revisableSteps.length > 0 && (
        <div className="mb-8">
          <h2 className="text-sm font-semibold text-slate-500 uppercase tracking-wide mb-4">
            Comparar con diseño base
          </h2>
          <div className="flex gap-3 flex-wrap">
            {revisableSteps.map((step) => (
              <button
                key={step}
                onClick={() => handleCompare(step)}
                disabled={comparing}
                className="flex items-center gap-2 bg-brand-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-brand-700 disabled:opacity-50 transition-colors"
              >
                <RefreshCw className={`w-4 h-4 ${comparing ? 'animate-spin' : ''}`} />
                {comparing ? 'Comparando...' : `Comparar ${STEP_LABELS[step]}`}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Resultado de comparación */}
      {activeComparison && (
        <div className="bg-white border border-slate-200 rounded-xl p-6">
          <h2 className="font-semibold text-slate-900 mb-4">Resultado de comparación</h2>

          {/* Scores */}
          <div className="grid grid-cols-3 gap-4 mb-6">
            {[
              { label: 'Similitud estructural', val: activeComparison.similarity_score },
              { label: 'Similitud de color', val: activeComparison.color_score },
              { label: 'Similitud de texto', val: activeComparison.ocr_score },
            ].map(({ label, val }) => (
              <div key={label} className="text-center p-3 bg-slate-50 rounded-lg">
                <div className={`text-2xl font-bold ${
                  val === null ? 'text-slate-400' :
                  val >= 0.9 ? 'text-green-600' :
                  val >= 0.7 ? 'text-yellow-600' : 'text-red-600'
                }`}>
                  {val !== null ? `${(val * 100).toFixed(1)}%` : 'N/A'}
                </div>
                <div className="text-xs text-slate-500 mt-1">{label}</div>
              </div>
            ))}
          </div>

          {/* Imagen anotada */}
          <div className="mb-6">
            <p className="text-sm font-medium text-slate-700 mb-2 flex items-center gap-1">
              <Eye className="w-4 h-4" /> Imagen con diferencias marcadas
            </p>
            <img
              src={(() => {
                const v = versions.find(x => x.id === activeComparison.revised_version_id)
                return v?.annotated_image_path ? labelsApi.staticUrl(v.annotated_image_path) : ''
              })()}
              alt="Comparación anotada"
              className="max-w-full rounded-lg border border-slate-200"
            />
            <div className="flex gap-4 mt-2 text-xs text-slate-500">
              <span className="flex items-center gap-1">
                <span className="w-3 h-3 bg-red-500 rounded-sm inline-block" /> Forma
              </span>
              <span className="flex items-center gap-1">
                <span className="w-3 h-3 bg-orange-400 rounded-sm inline-block" /> Color
              </span>
              <span className="flex items-center gap-1">
                <span className="w-3 h-3 bg-yellow-400 rounded-sm inline-block" /> Texto
              </span>
            </div>
          </div>

          {/* Diferencias */}
          {activeComparison.differences.length > 0 && (
            <div className="mb-6">
              <p className="text-sm font-medium text-slate-700 mb-2">
                Diferencias detectadas ({activeComparison.differences.length})
              </p>
              <div className="space-y-2 max-h-48 overflow-y-auto">
                {activeComparison.differences.map((d) => (
                  <div
                    key={d.id}
                    className="flex items-start gap-3 p-3 bg-slate-50 rounded-lg text-sm"
                  >
                    <span className={`px-2 py-0.5 rounded text-xs font-medium flex-shrink-0 ${
                      d.severity === 'ALTA' ? 'bg-red-100 text-red-700' :
                      d.severity === 'MEDIA' ? 'bg-yellow-100 text-yellow-700' :
                      'bg-slate-100 text-slate-600'
                    }`}>
                      {d.severity}
                    </span>
                    <div>
                      <span className="font-medium text-slate-800">{d.difference_type}</span>
                      {' · '}
                      <span className="text-slate-600">{d.description}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Review */}
          <div className="border-t border-slate-100 pt-4">
            <textarea
              rows={2}
              placeholder="Notas del revisor (opcional)..."
              value={reviewNotes}
              onChange={(e) => setReviewNotes(e.target.value)}
              className="w-full text-sm border border-slate-200 rounded-lg px-3 py-2 mb-3 focus:outline-none focus:ring-1 focus:ring-brand-500 resize-none"
            />
            <div className="flex gap-3">
              <button
                onClick={() => handleReview('RECHAZADO')}
                disabled={reviewLoading}
                className="flex items-center gap-2 border border-red-300 text-red-600 px-4 py-2 rounded-lg text-sm hover:bg-red-50 disabled:opacity-50 transition-colors"
              >
                <XCircle className="w-4 h-4" />
                Rechazar
              </button>
              <button
                onClick={() => handleReview('APROBADO')}
                disabled={reviewLoading}
                className="flex items-center gap-2 bg-green-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-green-700 disabled:opacity-50 transition-colors"
              >
                <CheckCircle className="w-4 h-4" />
                Aprobar
              </button>
              <button
                onClick={handleGenerateReport}
                className="flex items-center gap-2 border border-slate-300 text-slate-700 px-4 py-2 rounded-lg text-sm hover:bg-slate-50 transition-colors ml-auto"
              >
                <FileText className="w-4 h-4" />
                Generar reporte
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

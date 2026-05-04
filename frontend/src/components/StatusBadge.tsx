import type { ProjectStatus } from '../types'
import clsx from 'clsx'

const STATUS_LABELS: Record<ProjectStatus, string> = {
  BORRADOR: 'Borrador',
  EN_REVISION_REDISENO: 'En revisión (Rediseño)',
  EN_REVISION_IMPRENTA: 'En revisión (Imprenta)',
  VERIFICADA: 'Verificada',
  RECHAZADA: 'Rechazada',
}

const STATUS_COLORS: Record<ProjectStatus, string> = {
  BORRADOR: 'bg-slate-100 text-slate-600',
  EN_REVISION_REDISENO: 'bg-yellow-100 text-yellow-700',
  EN_REVISION_IMPRENTA: 'bg-blue-100 text-blue-700',
  VERIFICADA: 'bg-green-100 text-green-700',
  RECHAZADA: 'bg-red-100 text-red-700',
}

export function StatusBadge({ status }: { status: ProjectStatus }) {
  return (
    <span className={clsx('inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium', STATUS_COLORS[status])}>
      {STATUS_LABELS[status]}
    </span>
  )
}

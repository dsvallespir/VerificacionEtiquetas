/**
 * Parsea fechas ISO que pueden venir sin sufijo 'Z' (SQLite)
 * y las convierte a formato legible en español Argentina.
 */
export function parseDate(dateStr: string | null | undefined): Date {
  if (!dateStr) return new Date(NaN)
  // Normaliza: si no termina en Z ni tiene offset, agrega Z para UTC
  const normalized = /[Z+\-]\d*$/.test(dateStr) ? dateStr : `${dateStr}Z`
  return new Date(normalized)
}

export function formatDate(dateStr: string | null | undefined): string {
  if (!dateStr) return '—'
  const d = parseDate(dateStr)
  if (isNaN(d.getTime())) return '—'
  return d.toLocaleDateString('es-AR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  })
}

export function formatDateTime(dateStr: string | null | undefined): string {
  if (!dateStr) return '—'
  const d = parseDate(dateStr)
  if (isNaN(d.getTime())) return '—'
  return d.toLocaleString('es-AR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

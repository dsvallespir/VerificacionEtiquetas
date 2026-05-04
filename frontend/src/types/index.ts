// ─── Enumeraciones ────────────────────────────────────────────────────────────

export type ProjectStatus =
  | 'BORRADOR'
  | 'EN_REVISION_REDISENO'
  | 'EN_REVISION_IMPRENTA'
  | 'VERIFICADA'
  | 'RECHAZADA'

export type LabelStep = 'DISENO' | 'REDISENO' | 'MUESTRA_IMPRENTA'

export type DifferenceType =
  | 'TEXTO'
  | 'COLOR'
  | 'FORMA'
  | 'ELEMENTO_FALTANTE'
  | 'ELEMENTO_EXTRA'
  | 'GENERAL'

export type ComparisonStatus = 'PENDIENTE' | 'APROBADO' | 'RECHAZADO'

// ─── Entidades ────────────────────────────────────────────────────────────────

export interface User {
  id: number
  username: string
  email: string
  full_name: string | null
  is_active: boolean
  created_at: string
}

export interface Project {
  id: number
  name: string
  description: string | null
  product_name: string | null
  status: ProjectStatus
  created_at: string
  updated_at: string
  owner_id: number
  owner: User
}

export interface LabelVersion {
  id: number
  step: LabelStep
  image_path: string
  annotated_image_path: string | null
  notes: string | null
  uploaded_at: string
  project_id: number
  uploader: User | null
}

export interface Difference {
  id: number
  difference_type: DifferenceType
  description: string
  bbox_x: number | null
  bbox_y: number | null
  bbox_w: number | null
  bbox_h: number | null
  severity: string
  extra_data: Record<string, unknown> | null
}

export interface Comparison {
  id: number
  status: ComparisonStatus
  similarity_score: number | null
  ocr_score: number | null
  color_score: number | null
  compared_at: string
  reviewer_notes: string | null
  base_version_id: number
  revised_version_id: number
  differences: Difference[]
}

export interface Report {
  id: number
  title: string
  content: string | null
  generated_at: string
  file_path: string | null
  project_id: number
  comparison_id: number | null
}

// ─── Formularios ─────────────────────────────────────────────────────────────

export interface LoginForm {
  username: string
  password: string
}

export interface RegisterForm {
  username: string
  email: string
  full_name?: string
  password: string
}

export interface ProjectForm {
  name: string
  description?: string
  product_name?: string
}

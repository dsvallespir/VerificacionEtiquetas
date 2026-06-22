import api from './client'
import type {
  LoginForm,
  RegisterForm,
  User,
  Project,
  ProjectForm,
  LabelVersion,
  Comparison,
  Report,
  ComparisonStatus,
} from '../types'

// ─── Auth ─────────────────────────────────────────────────────────────────────

export const authApi = {
  login: async (data: LoginForm): Promise<string> => {
    const form = new URLSearchParams()
    form.append('username', data.username)
    form.append('password', data.password)
    const res = await api.post<{ access_token: string }>('/auth/login', form, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    })
    return res.data.access_token
  },

  register: async (data: RegisterForm): Promise<User> => {
    
    const res = await api.post<User>('/auth/register', data)
    console.log(res);
    return res.data
  },
}

// ─── Projects ────────────────────────────────────────────────────────────────

export const projectsApi = {
  list: async (): Promise<Project[]> => {
    const res = await api.get<Project[]>('/projects/')
    return res.data
  },

  get: async (id: number): Promise<Project> => {
    const res = await api.get<Project>(`/projects/${id}`)
    return res.data
  },

  create: async (data: ProjectForm): Promise<Project> => {
    const res = await api.post<Project>('/projects/', data)
    return res.data
  },

  update: async (id: number, data: Partial<ProjectForm>): Promise<Project> => {
    const res = await api.patch<Project>(`/projects/${id}`, data)
    return res.data
  },

  delete: async (id: number): Promise<void> => {
    await api.delete(`/projects/${id}`)
  },
}

// ─── Labels ──────────────────────────────────────────────────────────────────

export const labelsApi = {
  listVersions: async (projectId: number): Promise<LabelVersion[]> => {
    const res = await api.get<LabelVersion[]>(`/labels/${projectId}/versions`)
    return res.data
  },

  upload: async (
    projectId: number,
    step: string,
    file: File,
    notes?: string,
  ): Promise<LabelVersion> => {
    const form = new FormData()
    form.append('step', step)
    form.append('file', file)
    if (notes) form.append('notes', notes)
    const res = await api.post<LabelVersion>(`/labels/${projectId}/upload`, form)
    return res.data
  },

  compare: async (projectId: number, revisedVersionId: number): Promise<Comparison> => {
    const res = await api.post<Comparison>(
      `/labels/${projectId}/compare/${revisedVersionId}`,
    )
    return res.data
  },

  reviewComparison: async (
    comparisonId: number,
    status: ComparisonStatus,
    notes?: string,
  ): Promise<Comparison> => {
    const res = await api.patch<Comparison>(`/labels/comparisons/${comparisonId}/review`, {
      status,
      reviewer_notes: notes,
    })
    return res.data
  },

  // Extrae el nombre de archivo de la ruta guardada en DB (ej: "uploads/abc.jpg" → "/uploads/abc.jpg")
  // Método corregido con detección de entorno
  staticUrl: (imagePath: string) => {
    if (!imagePath) return '';
    
    // Si la ruta que viene de la DB ya incluye http/https, la devuelve tal cual
    if (imagePath.startsWith('http://') || imagePath.startsWith('https://')) {
      return imagePath;
    }

    // Detectamos si la app corre en producción (Railway) o en tu computadora
    const isProduction = window.location.hostname !== 'localhost';
    
    // Usamos la URL pública real de tu BACKEND en producción o el localhost.
    // En ambos casos incluye /api porque los uploads se montan en /api/uploads.
    const BACKEND_URL = isProduction
      ? 'https://verificacionetiquetas-production.up.railway.app/api'
      : 'http://localhost:8000/api';

    // Limpiamos barras duplicadas por si acaso imagePath ya empieza con /
    const cleanPath = imagePath.startsWith('/') ? imagePath : `/${imagePath}`;

    return `${BACKEND_URL}${cleanPath}`;
  }
}

// ─── Reports ─────────────────────────────────────────────────────────────────

export const reportsApi = {
  list: async (projectId: number): Promise<Report[]> => {
    const res = await api.get<Report[]>(`/reports/${projectId}`)
    return res.data
  },

  generate: async (projectId: number, comparisonId: number): Promise<Report> => {
    const res = await api.post<Report>(
      `/reports/${projectId}/generate?comparison_id=${comparisonId}`,
    )
    return res.data
  },

  get: async (reportId: number): Promise<Report> => {
    const res = await api.get<Report>(`/reports/detail/${reportId}`)
    return res.data
  },
}

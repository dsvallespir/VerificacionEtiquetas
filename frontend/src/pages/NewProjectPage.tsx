import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { projectsApi } from '../api/endpoints'
import { toast } from 'react-hot-toast'
import { ArrowLeft } from 'lucide-react'

export default function NewProjectPage() {
  const navigate = useNavigate()
  const [form, setForm] = useState({ name: '', description: '', product_name: '' })
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    try {
      const project = await projectsApi.create({
        name: form.name,
        description: form.description || undefined,
        product_name: form.product_name || undefined,
      })
      toast.success('Proyecto creado')
      navigate(`/projects/${project.id}`)
    } catch {
      toast.error('Error al crear el proyecto')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="p-8 max-w-xl">
      <button
        onClick={() => navigate('/projects')}
        className="flex items-center gap-1 text-sm text-slate-500 hover:text-slate-700 mb-6"
      >
        <ArrowLeft className="w-4 h-4" />
        Volver a proyectos
      </button>

      <h1 className="text-2xl font-bold text-slate-900 mb-6">Nuevo proyecto</h1>

      <form onSubmit={handleSubmit} className="space-y-5 bg-white border border-slate-200 rounded-xl p-6">
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">
            Nombre del proyecto *
          </label>
          <input
            type="text"
            required
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            className="w-full border border-slate-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-brand-500 text-sm"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">Producto</label>
          <input
            type="text"
            value={form.product_name}
            onChange={(e) => setForm({ ...form, product_name: e.target.value })}
            className="w-full border border-slate-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-brand-500 text-sm"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">Descripción</label>
          <textarea
            rows={3}
            value={form.description}
            onChange={(e) => setForm({ ...form, description: e.target.value })}
            className="w-full border border-slate-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-brand-500 text-sm resize-none"
          />
        </div>
        <div className="flex gap-3 pt-2">
          <button
            type="button"
            onClick={() => navigate('/projects')}
            className="flex-1 border border-slate-300 text-slate-700 py-2 rounded-lg text-sm hover:bg-slate-50 transition-colors"
          >
            Cancelar
          </button>
          <button
            type="submit"
            disabled={loading}
            className="flex-1 bg-brand-600 text-white py-2 rounded-lg text-sm font-medium hover:bg-brand-700 disabled:opacity-50 transition-colors"
          >
            {loading ? 'Creando...' : 'Crear proyecto'}
          </button>
        </div>
      </form>
    </div>
  )
}

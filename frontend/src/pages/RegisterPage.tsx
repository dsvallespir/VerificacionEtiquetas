import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { authApi } from '../api/endpoints'
import { toast } from 'react-hot-toast'
import { Tag } from 'lucide-react'

export default function RegisterPage() {
  const navigate = useNavigate()
  const [form, setForm] = useState({ username: '', email: '', full_name: '', password: '' })
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    try {
      await authApi.register(form)
      toast.success('Cuenta creada. Podés iniciar sesión.')
      navigate('/login')
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      toast.error(msg || 'Error al registrarse')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-900 to-brand-900">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-md p-8">
        <div className="flex items-center gap-3 mb-8">
          <div className="bg-brand-600 p-2 rounded-lg">
            <Tag className="w-6 h-6 text-white" />
          </div>
          <h1 className="text-xl font-bold text-slate-900">Crear cuenta</h1>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {(['username', 'email', 'full_name'] as const).map((field) => (
            <div key={field}>
              <label className="block text-sm font-medium text-slate-700 mb-1 capitalize">
                {field.replace('_', ' ')}
              </label>
              <input
                type={field === 'email' ? 'email' : 'text'}
                required={field !== 'full_name'}
                value={form[field]}
                onChange={(e) => setForm({ ...form, [field]: e.target.value })}
                className="w-full border border-slate-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-brand-500"
              />
            </div>
          ))}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Contraseña</label>
            <input
              type="password"
              required
              value={form.password}
              onChange={(e) => setForm({ ...form, password: e.target.value })}
              className="w-full border border-slate-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-brand-500"
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            className="w-full bg-brand-600 text-white py-2.5 rounded-lg font-medium hover:bg-brand-700 disabled:opacity-50 transition-colors"
          >
            {loading ? 'Registrando...' : 'Registrarse'}
          </button>
        </form>

        <p className="mt-4 text-center text-sm text-slate-500">
          ¿Ya tenés cuenta?{' '}
          <Link to="/login" className="text-brand-600 hover:underline font-medium">
            Iniciar sesión
          </Link>
        </p>
      </div>
    </div>
  )
}

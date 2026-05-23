import axios from 'axios'

// Detecta si la app corre en producción (Railway) o localmente
const isProduction = window.location.hostname !== 'localhost'

const api = axios.create({
  // URL de producción (reemplaza por la URL real de tu BACKEND) vs URL local
  baseURL: isProduction 
    ? 'https://verificacionetiquetas-production.up.railway.app/api' 
    : '/api', 
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (res) => res,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  },
)

export default api

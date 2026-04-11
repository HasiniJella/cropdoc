import axios from 'axios'

// In dev: proxied via vite to localhost:8000
// In prod: set VITE_API_URL to your Railway backend URL
const BASE = import.meta.env.VITE_API_URL || '/api'

export const api = axios.create({
  baseURL: BASE,
  timeout: 30000, // 30s — model inference can be slow on CPU
})

export const predictDisease = async (imageFile) => {
  const form = new FormData()
  form.append('file', imageFile)
  const { data } = await api.post('/predict', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}

export const speakText = (text, lang = 'te') => {
  const base = import.meta.env.VITE_API_URL || '/api'
  return `${base}/speak?text=${encodeURIComponent(text)}&lang=${lang}`
}

export const checkHealth = async () => {
  const { data } = await api.get('/health')
  return data
}
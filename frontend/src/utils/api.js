import axios from 'axios'

// ── Environment detection ─────────────────────────────────────────────
const isElectronProd = window.location.protocol === 'file:'

// FIX: Added missing port and full IP for Electron production
const BASE = isElectronProd
  ? 'http://127.0.0.1:8000' 
  : (import.meta.env.VITE_API_URL || '/api')

// ── Token storage helpers ─────────────────────────────────────────────
const TOKEN_KEY   = 'cropdoc_access_token'
const REFRESH_KEY = 'cropdoc_refresh_token'
const USER_KEY    = 'cropdoc_user'

export const saveAuth = (accessToken, refreshToken, user) => {
  localStorage.setItem(TOKEN_KEY,   accessToken);
  localStorage.setItem(REFRESH_KEY, refreshToken  || '');
  localStorage.setItem(USER_KEY,    JSON.stringify(user));
};

export const getToken        = () => localStorage.getItem(TOKEN_KEY)
export const getRefreshToken = () => localStorage.getItem(REFRESH_KEY)
export const getUser = () => {
  const u = localStorage.getItem(USER_KEY)
  if (!u || u === "undefined" || u === "null") return null
  try {
    const parsed = JSON.parse(u)
    if (parsed && typeof parsed === 'object' && (parsed.id || Object.keys(parsed).length > 0)) {
      return parsed
    }
    return null
  } catch (e) {
    console.error("Failed to parse user from storage", e)
    return null
  }
}

export const isLoggedIn = () => !!getToken()
export const logout     = () => {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(REFRESH_KEY)
  localStorage.removeItem(USER_KEY)
}

// ── Axios instance ────────────────────────────────────────────────────
export const api = axios.create({
  baseURL: BASE,
  timeout: 30000,
})

// Attach JWT to every request if available
api.interceptors.request.use((config) => {
  const token = getToken(); 
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
}, (error) => Promise.reject(error));

// Auto-refresh on 401 — then retry original request
api.interceptors.response.use(
  res => res,
  async err => {
    const original = err.config
    if (err.response?.status === 401 && getRefreshToken() && !original._retry) {
      original._retry = true
      try {
        const { data } = await axios.post(`${BASE}/refresh`, {
          refresh_token: getRefreshToken()
        })
        localStorage.setItem(TOKEN_KEY,   data.access_token)
        localStorage.setItem(REFRESH_KEY, data.refresh_token)
        original.headers.Authorization = `Bearer ${data.access_token}`
        return api(original)
      } catch {
        logout()
        window.location.href = '/'
      }
    }
    return Promise.reject(err)
  }
)

// ═══════════════════════════════════════════════════════════════════════
//  API FUNCTIONS
// ═══════════════════════════════════════════════════════════════════════

export const predictDisease = async (imageFile) => {
  const form = new FormData()
  form.append('file', imageFile)
  const { data } = await api.post('/predict', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}

export const speakText = (text, lang = 'te') =>
  `${BASE}/speak?text=${encodeURIComponent(text)}&lang=${lang}`

export const checkHealth = async () => {
  const { data } = await api.get('/health')
  return data
}

export const getLiveWeather = async (lat, lon) => {
  const { data } = await api.get(`/weather?lat=${lat}&lon=${lon}`)
  return data
}

export const getMarketPrices = async (commodity = '', state = '') => {
  try {
    const url = `/market-prices?limit=100` + (commodity ? `&commodity=${commodity}` : '') + (state ? `&state=${state}` : '')
    const { data } = await api.get(url)
    return data
  } catch (error) {
    console.error("Error fetching market data:", error)
    throw error
  }
}

export const registerUser  = async (data) => (await api.post('/register', data)).data
export const loginUser     = async (data) => (await api.post('/login', data)).data
export const getMe         = async () => (await api.get('/me')).data
export const updateProfile = async (data) => (await api.put('/me', data)).data
export const getHistory    = async (limit = 20) => (await api.get(`/history?limit=${limit}`)).data
export const deleteHistory = async (id) => (await api.delete(`/history/${id}`)).data

// ONLY ONE DEFAULT EXPORT AT THE VERY BOTTOM
export default api;

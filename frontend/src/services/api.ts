import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true,  // send httpOnly refresh cookie
})

// ── Access token — stored in memory (Pinia), never in localStorage ──
let accessToken: string | null = null

export function setAccessToken(token: string | null) {
  accessToken = token
}

export function getAccessToken(): string | null {
  return accessToken
}

let isRefreshing = false
let failedQueue: Array<{
  resolve: (token: string) => void
  reject: (error: unknown) => void
}> = []

function processQueue(error: unknown, token: string | null) {
  failedQueue.forEach(({ resolve, reject }) => {
    if (error) {
      reject(error)
    } else if (token) {
      resolve(token)
    }
  })
  failedQueue = []
}

api.interceptors.request.use((config) => {
  if (accessToken) {
    config.headers.Authorization = `Bearer ${accessToken}`
  }
  return config
})

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config

    if (error.response?.status === 401 && !originalRequest._retry) {
      // Never attempt a token refresh from an anonymous auth endpoint — a
      // 401 there (bad password, bad token) is a final answer, not a session
      // expiry.  Authenticated endpoints (e.g. /auth/me/ used to restore the
      // session after a page reload) SHOULD attempt refresh.
      const anonymousAuthEndpoints = [
        '/auth/login/',
        '/auth/register/',
        '/auth/google/',
        '/auth/verify-email/',
        '/auth/resend-verification/',
        '/auth/reset-password/',
      ]
      const isAnonymousAuthEndpoint = anonymousAuthEndpoints.some((ep) =>
        originalRequest.url?.includes(ep),
      )
      if (isAnonymousAuthEndpoint) {
        accessToken = null
        return Promise.reject(error)
      }

      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject })
        }).then((token) => {
          originalRequest.headers.Authorization = `Bearer ${token}`
          return api(originalRequest)
        })
      }

      originalRequest._retry = true
      isRefreshing = true

      try {
        // Refresh token is sent as httpOnly cookie automatically
        const response = await axios.post(
          '/api/auth/token/refresh/',
          {},
          { withCredentials: true },
        )
        const newAccess = response.data.access
        accessToken = newAccess

        processQueue(null, newAccess)

        originalRequest.headers.Authorization = `Bearer ${newAccess}`
        return api(originalRequest)
      } catch (refreshError) {
        processQueue(refreshError, null)
        accessToken = null
        return Promise.reject(refreshError)
      } finally {
        isRefreshing = false
      }
    }

    return Promise.reject(error)
  },
)

export default api

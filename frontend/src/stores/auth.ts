import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/services/api'

interface User {
  id: number
  email: string
  first_name: string
  last_name: string
  phone: string
  is_verified: boolean
  is_staff: boolean
}

export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(null)
  const isAuthenticated = ref(false)

  function setTokens(access: string, refresh: string) {
    localStorage.setItem('access_token', access)
    localStorage.setItem('refresh_token', refresh)
    isAuthenticated.value = true
  }

  function clearTokens() {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    user.value = null
    isAuthenticated.value = false
  }

  async function fetchUser() {
    try {
      const response = await api.get('/auth/me/')
      user.value = response.data
      isAuthenticated.value = true
    } catch {
      clearTokens()
    }
  }

  async function login(email: string, password: string) {
    const response = await api.post('/auth/login/', { email, password })
    setTokens(response.data.access, response.data.refresh)
    user.value = response.data.user
  }

  async function register(data: {
    email: string
    first_name: string
    last_name: string
    phone: string
    password: string
    password2: string
  }) {
    await api.post('/auth/register/', data)
    // No auto-login — user must verify email first
  }

  async function verifyEmail(uid: string, token: string) {
    const response = await api.post('/auth/verify-email/', { uid, token })
    return response.data
  }

  async function resendVerification(email: string) {
    await api.post('/auth/resend-verification/', { email })
  }

  async function logout() {
    const refresh = localStorage.getItem('refresh_token')
    if (refresh) {
      try {
        await api.post('/auth/logout/', { refresh })
      } catch {
        // proceed with client-side cleanup regardless
      }
    }
    clearTokens()
  }

  return { user, isAuthenticated, login, register, verifyEmail, resendVerification, logout, fetchUser }
})


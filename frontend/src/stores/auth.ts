import { defineStore } from 'pinia'
import { ref } from 'vue'
import api, { setAccessToken } from '@/services/api'

interface User {
  id: number
  email: string
  first_name: string
  last_name: string
  phone: string
  is_verified: boolean
  is_staff: boolean
  identity_locked?: boolean
}

export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(null)
  const isAuthenticated = ref(false)
  const unreadNotificationCount = ref(0)

  function setAuth(access: string, userData: User) {
    setAccessToken(access)
    user.value = userData
    isAuthenticated.value = true
  }

  function clearAuth() {
    setAccessToken(null)
    user.value = null
    isAuthenticated.value = false
    unreadNotificationCount.value = 0
  }

  async function fetchUnreadCount() {
    if (!isAuthenticated.value) return
    try {
      const response = await api.get('/notifications/?limit=1')
      unreadNotificationCount.value = response.data.unread_count || 0
    } catch { /* ignore */ }
  }

  async function fetchUser() {
    try {
      const response = await api.get('/auth/me/')
      user.value = response.data
      isAuthenticated.value = true
      await fetchUnreadCount()
    } catch {
      clearAuth()
    }
  }

  async function login(email: string, password: string) {
    const response = await api.post('/auth/login/', { email, password })
    setAuth(response.data.access, response.data.user)
    await fetchUnreadCount()
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
    try {
      await api.post('/auth/logout/', {})
    } catch {
      // proceed with client-side cleanup regardless
    }
    clearAuth()
  }

  return { user, isAuthenticated, unreadNotificationCount, login, register, verifyEmail, resendVerification, logout, fetchUser, fetchUnreadCount }
})


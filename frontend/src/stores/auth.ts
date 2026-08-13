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
  auth_method: 'email' | 'google'
  profile_complete?: boolean
  identity_complete?: boolean
  booking_eligible?: boolean
  profile_locked?: boolean
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

  async function loginWithGoogle(credential: string) {
    const response = await api.post('/auth/google/', { credential })
    setAuth(response.data.access, response.data.user)
    await fetchUnreadCount()
  }

  async function register(data: {
    email: string
    password: string
    password2: string
  }) {
    await api.post('/auth/register/', data)
    // No auto-login — user must verify email first
  }

  async function updateProfile(data: {
    first_name: string
    last_name: string
    phone: string
  }) {
    const response = await api.put('/auth/me/', data)
    user.value = response.data
    return response.data
  }

  async function changePassword(data: {
    current_password: string
    new_password: string
    new_password2: string
  }) {
    const response = await api.post('/auth/change-password/', data)
    return response.data
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

  return { user, isAuthenticated, unreadNotificationCount, login, loginWithGoogle, register, updateProfile, changePassword, verifyEmail, resendVerification, logout, fetchUser, fetchUnreadCount }
})


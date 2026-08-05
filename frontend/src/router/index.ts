import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'home',
      component: () => import('@/views/HomeView.vue'),
    },
    {
      path: '/vehicles',
      name: 'vehicles',
      component: () => import('@/views/VehicleListView.vue'),
    },
    {
      path: '/vehicles/:id',
      name: 'vehicle-detail',
      component: () => import('@/views/VehicleDetailView.vue'),
    },
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/LoginView.vue'),
      meta: { guestOnly: true },
    },
    {
      path: '/register',
      name: 'register',
      component: () => import('@/views/RegisterView.vue'),
      meta: { guestOnly: true },
    },
    {
      path: '/forgot-password',
      name: 'forgot-password',
      component: () => import('@/views/ForgotPasswordView.vue'),
      meta: { guestOnly: true },
    },
    {
      path: '/reset-password/:uid/:token',
      name: 'reset-password',
      component: () => import('@/views/ResetPasswordView.vue'),
    },
    {
      path: '/verify-email/:uid/:token',
      name: 'verify-email',
      component: () => import('@/views/VerifyEmailView.vue'),
    },
    {
      path: '/profile',
      name: 'profile',
      component: () => import('@/views/ProfileView.vue'),
      meta: { requiresAuth: true },
    },
  ],
})

router.beforeEach(async (to, _from, next) => {
  // Attempt to restore user from existing token
  const token = localStorage.getItem('access_token')
  const auth = useAuthStore()

  if (token && !auth.user) {
    try {
      await auth.fetchUser()
    } catch {
      // token invalid — clear and proceed
    }
  }

  if (to.meta.requiresAuth && !auth.isAuthenticated) {
    next({ name: 'login' })
  } else if (to.meta.guestOnly && auth.isAuthenticated) {
    next({ name: 'home' })
  } else {
    next()
  }
})

export default router

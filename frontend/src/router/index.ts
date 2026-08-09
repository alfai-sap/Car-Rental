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
      path: '/vehicles/:id/book',
      name: 'vehicle-book',
      component: () => import('@/views/BookingView.vue'),
      meta: { requiresAuth: true },
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
    {
      path: '/dashboard',
      name: 'customer-dashboard',
      component: () => import('@/views/CustomerDashboardView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/transactions/:id',
      name: 'transaction',
      component: () => import('@/views/TransactionView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/admin/transactions/:id',
      name: 'admin-transaction',
      component: () => import('@/views/AdminTransactionView.vue'),
      meta: { requiresAuth: true, requiresStaff: true },
    },
    {
      path: '/admin/dashboard',
      name: 'admin-dashboard',
      component: () => import('@/views/AdminDashboardView.vue'),
      meta: { requiresAuth: true, requiresStaff: true },
    },
    {
      path: '/admin/login',
      name: 'admin-login',
      component: () => import('@/views/AdminLoginView.vue'),
      meta: { guestOnly: true },
    },
    {
      path: '/admin/vehicles',
      name: 'admin-vehicles',
      component: () => import('@/views/AdminVehiclesView.vue'),
      meta: { requiresAuth: true, requiresStaff: true },
    },
    {
      path: '/admin/vehicles/:id',
      name: 'admin-vehicle-detail',
      component: () => import('@/views/AdminVehicleDetailView.vue'),
      meta: { requiresAuth: true, requiresStaff: true },
    },
    {
      path: '/notifications',
      name: 'notifications',
      component: () => import('@/views/NotificationsView.vue'),
      meta: { requiresAuth: true },
    },
  ],
})

router.beforeEach(async (to, _from, next) => {
  const auth = useAuthStore()

  // Attempt to restore user session via httpOnly refresh cookie
  if (!auth.user) {
    try {
      await auth.fetchUser()
    } catch {
      // Not authenticated — proceed as guest
    }
  }

  if (to.meta.requiresAuth && !auth.isAuthenticated) {
    next({ name: 'login', query: { redirect: to.fullPath } })
  } else if (to.meta.requiresStaff && !auth.user?.is_staff) {
    // Non-staff user trying to access admin-only pages
    next({ name: 'home' })
  } else if (to.meta.guestOnly && auth.isAuthenticated) {
    if (auth.user?.is_staff) {
      next({ name: 'admin-dashboard' })
    } else {
      next({ name: 'home' })
    }
  } else if (auth.isAuthenticated && auth.user?.is_staff) {
    if (to.name === 'home') {
      next({ name: 'admin-dashboard' })
    } else if (to.name === 'vehicle-book' || to.name === 'customer-dashboard' || to.name === 'profile') {
      next({ name: 'admin-dashboard' })
    } else {
      next()
    }
  } else {
    next()
  }
})

export default router

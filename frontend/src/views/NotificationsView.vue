<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { RouterLink } from 'vue-router'
import Navbar from '@/components/Navbar.vue'
import api from '@/services/api'
import { useAuthStore } from '@/stores/auth'
import {
  Bell, CheckCircle, XCircle, Clock, AlertCircle,
  CreditCard, Car, ChevronLeft, ChevronRight,
} from 'lucide-vue-next'

const auth = useAuthStore()

interface Notification {
  id: number
  notification_type: string
  type_display: string
  title: string
  message: string
  booking_id: number | null
  booking_number: string | null
  is_read: boolean
  link: string
  created_at: string
}

const loading = ref(true)
const error = ref('')
const notifications = ref<Notification[]>([])
const unreadCount = ref(0)

// â”€â”€ Pagination â”€â”€
const PER_PAGE = 10
const currentPage = ref(1)
const totalCount = ref(0)

const totalPages = computed(() => Math.max(1, Math.ceil(totalCount.value / PER_PAGE)))

function goToPage(page: number) {
  if (page < 1 || page > totalPages.value) return
  currentPage.value = page
  fetchNotifications()
}

function notificationIcon(type: string) {
  switch (type) {
    case 'booking_confirmed':
    case 'payment_successful':
    case 'transaction_completed':
      return CheckCircle
    case 'booking_rejected':
      return XCircle
    case 'booking_approved':
    case 'booking_submitted':
    case 'payment_required':
    case 'pickup_reminder':
      return Clock
    case 'unit_assigned':
    case 'unit_changed':
      return Car
    case 'rental_activated':
      return Car
    case 'vehicle_returned':
      return CreditCard
    default:
      return Bell
  }
}

function notificationColor(type: string): string {
  switch (type) {
    case 'booking_confirmed':
    case 'payment_successful':
    case 'transaction_completed':
      return 'text-green-600'
    case 'booking_rejected':
    case 'payment_failed':
      return 'text-red-600'
    case 'payment_required':
    case 'additional_payment_required':
      return 'text-amber-600'
    case 'rental_activated':
      return 'text-blue-600'
    case 'unit_assigned':
    case 'unit_changed':
      return 'text-purple-600'
    default:
      return 'text-zinc-500'
  }
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString('en-PH', {
    month: 'short', day: 'numeric', year: 'numeric',
  })
}

function formatTime(dateStr: string): string {
  return new Date(dateStr).toLocaleTimeString('en-PH', {
    hour: '2-digit', minute: '2-digit',
  })
}

async function markAllRead() {
  try {
    await api.post('/notifications/', { mark_all: true })
    notifications.value.forEach(n => n.is_read = true)
    unreadCount.value = 0
    auth.unreadNotificationCount = 0
  } catch { /* ignore */ }
}

async function fetchNotifications() {
  loading.value = true
  const offset = (currentPage.value - 1) * PER_PAGE
  try {
    const response = await api.get(`/notifications/?limit=${PER_PAGE}&offset=${offset}`)
    notifications.value = response.data.notifications
    unreadCount.value = response.data.unread_count || 0
    totalCount.value = response.data.count || 0
    auth.unreadNotificationCount = unreadCount.value
  } catch {
    error.value = 'Failed to load notifications.'
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchNotifications()
})
</script>

<template>
  <div class="min-h-screen flex flex-col bg-zinc-50">
    <Navbar />

    <main class="flex-1 max-w-2xl mx-auto px-4 pt-24 pb-16 w-full">
      <div class="flex items-center justify-between mb-6">
        <h1 class="text-2xl font-semibold text-zinc-900">Notifications</h1>
        <button v-if="unreadCount > 0" @click="markAllRead" class="text-xs text-blue-600 hover:text-blue-800">
          Mark all as read ({{ unreadCount }})
        </button>
      </div>

      <div v-if="loading" class="text-center py-12">
        <p class="text-sm text-zinc-500">Loading notifications...</p>
      </div>

      <div v-else-if="error" class="text-center py-12">
        <p class="text-sm text-red-600">{{ error }}</p>
      </div>

      <div v-else-if="notifications.length === 0" class="text-center py-16">
        <div class="inline-flex items-center justify-center w-16 h-16 rounded-full bg-zinc-100 mb-4">
          <Bell class="h-8 w-8 text-zinc-400" />
        </div>
        <h2 class="text-lg font-medium text-zinc-900 mb-2">No notifications</h2>
        <p class="text-sm text-zinc-500">Updates about your bookings will appear here.</p>
      </div>

      <div v-else class="space-y-2">
        <div
          v-for="notif in notifications"
          :key="notif.id"
          class="block rounded-lg border border-zinc-200 bg-surface p-4 hover:border-zinc-300 transition-colors"
          :class="{ 'border-l-4 border-l-blue-500': !notif.is_read }"
        >
          <RouterLink
            v-if="notif.link"
            :to="notif.link"
            class="block"
          >
            <div class="flex items-start gap-3">
              <component
                :is="notificationIcon(notif.notification_type)"
                class="h-5 w-5 mt-0.5 flex-shrink-0"
                :class="notificationColor(notif.notification_type)"
              />
              <div class="flex-1 min-w-0">
                <p class="text-sm font-medium text-zinc-900">{{ notif.title }}</p>
                <p class="text-sm text-zinc-600">{{ notif.message }}</p>
                <p class="text-xs text-zinc-400 mt-1">
                  {{ formatDate(notif.created_at) }} at {{ formatTime(notif.created_at) }}
                  <span v-if="notif.booking_number">Â· {{ notif.booking_number }}</span>
                </p>
              </div>
            </div>
          </RouterLink>
          <div v-else class="flex items-start gap-3">
            <component
              :is="notificationIcon(notif.notification_type)"
              class="h-5 w-5 mt-0.5 flex-shrink-0"
              :class="notificationColor(notif.notification_type)"
            />
            <div class="flex-1 min-w-0">
              <p class="text-sm font-medium text-zinc-900">{{ notif.title }}</p>
              <p class="text-sm text-zinc-600">{{ notif.message }}</p>
              <p class="text-xs text-zinc-400 mt-1">
                {{ formatDate(notif.created_at) }} at {{ formatTime(notif.created_at) }}
              </p>
            </div>
          </div>
        </div>

        <!-- Pagination -->
        <div v-if="totalPages > 1" class="flex items-center justify-center gap-1 pt-4">
          <button
            @click="goToPage(currentPage - 1)"
            :disabled="currentPage === 1"
            class="h-8 w-8 rounded flex items-center justify-center text-zinc-500 hover:bg-zinc-100 disabled:opacity-30 disabled:cursor-not-allowed"
          >
            <ChevronLeft class="h-4 w-4" />
          </button>
          <button
            v-for="page in totalPages"
            :key="page"
            @click="goToPage(page)"
            class="h-8 w-8 rounded text-sm font-medium transition-colors"
            :class="page === currentPage ? 'bg-ink text-ink-foreground' : 'text-zinc-600 hover:bg-zinc-100'"
          >
            {{ page }}
          </button>
          <button
            @click="goToPage(currentPage + 1)"
            :disabled="currentPage === totalPages"
            class="h-8 w-8 rounded flex items-center justify-center text-zinc-500 hover:bg-zinc-100 disabled:opacity-30 disabled:cursor-not-allowed"
          >
            <ChevronRight class="h-4 w-4" />
          </button>
        </div>
      </div>
    </main>
  </div>
</template>

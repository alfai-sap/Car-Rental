<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import Navbar from '@/components/Navbar.vue'
import api from '@/services/api'
import {
  Bell, CheckCircle, XCircle, Clock, AlertCircle,
  CreditCard, Car,
} from 'lucide-vue-next'

interface Notification {
  id: number
  booking_number: string
  vehicle_name: string
  status: string
  status_display: string
  message: string
  timestamp: string
  pickup_date: string
  return_date: string
}

const loading = ref(true)
const error = ref('')
const notifications = ref<Notification[]>([])

function statusIcon(status: string) {
  switch (status) {
    case 'confirmed':
    case 'completed':
      return CheckCircle
    case 'rejected':
      return XCircle
    case 'awaiting_payment':
    case 'pending_approval':
      return Clock
    case 'active':
      return Car
    case 'cancelled':
      return XCircle
    default:
      return Bell
  }
}

function statusColor(status: string): string {
  switch (status) {
    case 'confirmed':
    case 'completed':
      return 'text-green-600'
    case 'rejected':
    case 'cancelled':
      return 'text-red-600'
    case 'awaiting_payment':
      return 'text-amber-600'
    case 'active':
      return 'text-blue-600'
    case 'pending_approval':
      return 'text-zinc-500'
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

onMounted(async () => {
  try {
    const response = await api.get('/notifications/')
    notifications.value = response.data.notifications
  } catch {
    error.value = 'Failed to load notifications.'
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="min-h-screen flex flex-col bg-zinc-50">
    <Navbar />

    <main class="flex-1 max-w-2xl mx-auto px-4 pt-24 pb-16 w-full">
      <div class="flex items-center gap-3 mb-8">
        <Bell class="h-5 w-5 text-zinc-700" />
        <h1 class="text-2xl font-semibold text-zinc-900">Notifications</h1>
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
        <RouterLink
          v-for="notif in notifications"
          :key="notif.id"
          :to="`/transactions/${notif.id}`"
          class="block rounded-lg border border-zinc-200 bg-white p-4 hover:border-zinc-300 transition-colors"
        >
          <div class="flex items-start gap-3">
            <component
              :is="statusIcon(notif.status)"
              class="h-5 w-5 mt-0.5 flex-shrink-0"
              :class="statusColor(notif.status)"
            />
            <div class="flex-1 min-w-0">
              <p class="text-sm text-zinc-900">{{ notif.message }}</p>
              <p class="text-xs text-zinc-400 mt-1">
                {{ formatDate(notif.timestamp) }} at {{ formatTime(notif.timestamp) }}
                · {{ notif.booking_number }}
              </p>
            </div>
            <span class="text-xs text-zinc-400 flex-shrink-0">
              {{ notif.status_display }}
            </span>
          </div>
        </RouterLink>
      </div>
    </main>
  </div>
</template>

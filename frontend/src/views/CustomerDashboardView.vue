<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { RouterLink } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import Navbar from '@/components/Navbar.vue'
import Button from '@/components/ui/Button.vue'
import api from '@/services/api'
import {
  Clock, CheckCircle, XCircle, Car, AlertCircle,
  ChevronDown, ChevronUp, ExternalLink,
} from 'lucide-vue-next'

const auth = useAuthStore()

interface BookingSummary {
  total: number
  pending_approval: number
  approved: number
  awaiting_payment: number
  confirmed: number
  active: number
  completed: number
  cancelled: number
  rejected: number
}

interface BookingItem {
  id: number
  booking_number: string
  vehicle: number
  vehicle_name: string
  vehicle_image: string | null
  pickup_date: string
  return_date: string
  pickup_time: string
  return_time: string
  rental_days: number
  subtotal: string
  estimated_total: string
  status: string
  status_display: string
  special_request: string
  rejection_reason: string
  created_at: string
  updated_at: string
}

const loading = ref(true)
const error = ref('')
const summary = ref<BookingSummary | null>(null)
const bookings = ref<BookingItem[]>([])
const expandedId = ref<number | null>(null)
const cancellingId = ref<number | null>(null)
const payingId = ref<number | null>(null)

const STATUS_TABS = [
  { key: 'all', label: 'All' },
  { key: 'pending_approval', label: 'Pending' },
  { key: 'approved', label: 'Approved' },
  { key: 'awaiting_payment', label: 'Awaiting Payment' },
  { key: 'confirmed', label: 'Confirmed' },
  { key: 'active', label: 'Active' },
  { key: 'completed', label: 'Completed' },
  { key: 'cancelled', label: 'Cancelled' },
  { key: 'rejected', label: 'Rejected' },
] as const

const activeTab = ref<string>('all')

const filteredBookings = computed(() => {
  if (activeTab.value === 'all') return bookings.value
  return bookings.value.filter(b => b.status === activeTab.value)
})

function statusBadgeClass(status: string): string {
  switch (status) {
    case 'pending_approval': return 'bg-amber-100 text-amber-800'
    case 'approved': return 'bg-blue-100 text-blue-800'
    case 'awaiting_payment': return 'bg-purple-100 text-purple-800'
    case 'confirmed': return 'bg-green-100 text-green-800'
    case 'active': return 'bg-emerald-100 text-emerald-800'
    case 'completed': return 'bg-zinc-100 text-zinc-800'
    case 'cancelled': return 'bg-red-100 text-red-800'
    case 'rejected': return 'bg-red-100 text-red-800'
    default: return 'bg-zinc-100 text-zinc-800'
  }
}

function formatDate(dateStr: string): string {
  return new Date(dateStr + 'T00:00:00').toLocaleDateString('en-US', {
    month: 'short', day: 'numeric', year: 'numeric',
  })
}

function formatTime(timeStr: string): string {
  const [h, m] = timeStr.split(':')
  const hour = parseInt(h)
  const ampm = hour >= 12 ? 'PM' : 'AM'
  const display = hour > 12 ? hour - 12 : hour === 0 ? 12 : hour
  return `${display}:${m} ${ampm}`
}

function toggleExpanded(id: number) {
  expandedId.value = expandedId.value === id ? null : id
}

async function cancelBooking(bookingId: number) {
  cancellingId.value = bookingId
  try {
    await api.post(`/bookings/${bookingId}/cancel/`)
    await fetchDashboard()
  } catch {
    // ignore
  } finally {
    cancellingId.value = null
  }
}

async function initiatePayment(bookingId: number) {
  payingId.value = bookingId
  try {
    const response = await api.post('/payments/create-session/', { booking_id: bookingId })
    // Redirect to PayMongo checkout
    if (response.data.checkout_url) {
      window.location.href = response.data.checkout_url
    }
  } catch {
    // ignore
  } finally {
    payingId.value = null
  }
}

async function fetchDashboard() {
  loading.value = true
  error.value = ''
  try {
    const response = await api.get('/dashboard/customer/')
    summary.value = response.data.summary
    bookings.value = response.data.bookings
  } catch {
    error.value = 'Failed to load dashboard.'
  } finally {
    loading.value = false
  }
}

function statusIcon(status: string) {
  switch (status) {
    case 'pending_approval': return Clock
    case 'approved': return CheckCircle
    case 'awaiting_payment': return AlertCircle
    case 'confirmed': return CheckCircle
    case 'active': return Car
    case 'completed': return CheckCircle
    case 'cancelled': return XCircle
    case 'rejected': return XCircle
    default: return Clock
  }
}

onMounted(() => {
  fetchDashboard()
})
</script>

<template>
  <div class="min-h-screen flex flex-col bg-zinc-50">
    <Navbar />

    <main class="flex-1 max-w-5xl mx-auto px-4 pt-24 pb-16 w-full">
      <!-- Header -->
      <div class="mb-8">
        <h1 class="text-2xl font-semibold text-zinc-900">My Dashboard</h1>
        <p class="text-sm text-zinc-500 mt-1">Track your booking requests and rental history.</p>
      </div>

      <!-- Loading -->
      <div v-if="loading" class="text-center py-20">
        <p class="text-sm text-zinc-500">Loading dashboard...</p>
      </div>

      <!-- Error -->
      <div v-else-if="error" class="text-center py-20">
        <p class="text-sm text-red-600">{{ error }}</p>
      </div>

      <template v-else>
        <!-- Summary Cards -->
        <div v-if="summary" class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3 mb-8">
          <div class="rounded-md border border-amber-200 bg-amber-50 p-4">
            <p class="text-2xl font-bold text-amber-800">{{ summary.pending_approval }}</p>
            <p class="text-xs text-amber-600 mt-1">Pending</p>
          </div>
          <div class="rounded-md border border-blue-200 bg-blue-50 p-4">
            <p class="text-2xl font-bold text-blue-800">{{ summary.approved }}</p>
            <p class="text-xs text-blue-600 mt-1">Approved</p>
          </div>
          <div class="rounded-md border border-green-200 bg-green-50 p-4">
            <p class="text-2xl font-bold text-green-800">{{ summary.confirmed }}</p>
            <p class="text-xs text-green-600 mt-1">Confirmed</p>
          </div>
          <div class="rounded-md border border-emerald-200 bg-emerald-50 p-4">
            <p class="text-2xl font-bold text-emerald-800">{{ summary.active }}</p>
            <p class="text-xs text-emerald-600 mt-1">Active</p>
          </div>
          <div class="rounded-md border border-zinc-200 bg-zinc-50 p-4">
            <p class="text-2xl font-bold text-zinc-800">{{ summary.completed }}</p>
            <p class="text-xs text-zinc-500 mt-1">Completed</p>
          </div>
        </div>

        <!-- No bookings state -->
        <div v-if="bookings.length === 0" class="text-center py-16">
          <div class="inline-flex items-center justify-center w-16 h-16 rounded-full bg-zinc-100 mb-4">
            <Car class="h-8 w-8 text-zinc-400" />
          </div>
          <h2 class="text-lg font-medium text-zinc-900 mb-2">No bookings yet</h2>
          <p class="text-sm text-zinc-500 mb-6">Browse available vehicles to make your first booking.</p>
          <RouterLink to="/vehicles">
            <Button>Browse Vehicles</Button>
          </RouterLink>
        </div>

        <!-- Status Tabs -->
        <div v-if="bookings.length > 0" class="flex flex-wrap gap-1.5 mb-6">
          <button
            v-for="tab in STATUS_TABS"
            :key="tab.key"
            @click="activeTab = tab.key"
            class="px-3 py-1.5 text-xs font-medium rounded-md transition-colors"
            :class="activeTab === tab.key
              ? 'bg-zinc-900 text-white'
              : 'bg-white border border-zinc-200 text-zinc-600 hover:bg-zinc-50'"
          >
            {{ tab.label }}
            <span
              v-if="tab.key !== 'all' && summary"
              class="ml-1 opacity-60"
            >
              ({{ (summary as Record<string, number>)[tab.key] || 0 }})
            </span>
          </button>
        </div>

        <!-- Bookings List -->
        <div v-if="filteredBookings.length > 0" class="space-y-3">
          <div
            v-for="booking in filteredBookings"
            :key="booking.id"
            class="rounded-md border border-zinc-200 bg-white overflow-hidden"
          >
            <!-- Header row -->
            <button
              @click="toggleExpanded(booking.id)"
              class="w-full flex items-center gap-4 px-4 py-3 text-left hover:bg-zinc-50 transition-colors"
            >
              <!-- Vehicle image -->
              <div class="h-12 w-16 rounded bg-zinc-100 overflow-hidden flex-shrink-0">
                <img
                  v-if="booking.vehicle_image"
                  :src="booking.vehicle_image"
                  :alt="booking.vehicle_name"
                  class="h-full w-full object-cover"
                />
                <div v-else class="h-full w-full flex items-center justify-center">
                  <Car class="h-5 w-5 text-zinc-400" />
                </div>
              </div>

              <div class="flex-1 min-w-0">
                <p class="text-sm font-medium text-zinc-900 truncate">{{ booking.vehicle_name }}</p>
                <p class="text-xs text-zinc-500">
                  {{ formatDate(booking.pickup_date) }} — {{ formatDate(booking.return_date) }}
                  ({{ booking.rental_days }} day{{ booking.rental_days > 1 ? 's' : '' }})
                </p>
              </div>

              <span
                class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium flex-shrink-0"
                :class="statusBadgeClass(booking.status)"
              >
                <component :is="statusIcon(booking.status)" class="h-3 w-3" />
                {{ booking.status_display }}
              </span>

              <component :is="expandedId === booking.id ? ChevronUp : ChevronDown" class="h-4 w-4 text-zinc-400 flex-shrink-0" />
            </button>

            <!-- Expanded detail -->
            <div v-if="expandedId === booking.id" class="border-t border-zinc-100 px-4 py-4 bg-zinc-50 space-y-3">
              <div class="grid grid-cols-2 sm:grid-cols-4 gap-4">
                <div>
                  <p class="text-xs text-zinc-400">Booking #</p>
                  <p class="text-sm font-mono text-zinc-900">{{ booking.booking_number }}</p>
                </div>
                <div>
                  <p class="text-xs text-zinc-400">Pickup</p>
                  <p class="text-sm text-zinc-900">{{ formatDate(booking.pickup_date) }} at {{ formatTime(booking.pickup_time) }}</p>
                </div>
                <div>
                  <p class="text-xs text-zinc-400">Return</p>
                  <p class="text-sm text-zinc-900">{{ formatDate(booking.return_date) }} at {{ formatTime(booking.return_time) }}</p>
                </div>
                <div>
                  <p class="text-xs text-zinc-400">Estimated Total</p>
                  <p class="text-sm font-semibold text-zinc-900">₱{{ Number(booking.estimated_total).toLocaleString('en-PH') }}</p>
                </div>
              </div>

              <div v-if="booking.special_request">
                <p class="text-xs text-zinc-400">Special Request</p>
                <p class="text-sm text-zinc-700">{{ booking.special_request }}</p>
              </div>

              <div v-if="booking.rejection_reason" class="rounded-md bg-red-50 border border-red-200 p-3">
                <p class="text-xs font-medium text-red-800 mb-0.5">Rejection Reason</p>
                <p class="text-sm text-red-700">{{ booking.rejection_reason }}</p>
              </div>

              <div class="flex items-center gap-2 pt-1">
                <RouterLink
                  :to="`/vehicles/${booking.vehicle}`"
                  class="inline-flex items-center gap-1 text-xs text-zinc-500 hover:text-zinc-900"
                >
                  <ExternalLink class="h-3 w-3" /> View Vehicle
                </RouterLink>

                <RouterLink
                  :to="`/transactions/${booking.id}`"
                  class="inline-flex items-center gap-1 text-xs text-zinc-500 hover:text-zinc-900"
                >
                  <ExternalLink class="h-3 w-3" /> View Transaction
                </RouterLink>

                <!-- Cancel button (for pending_approval, approved, awaiting_payment) -->
                <button
                  v-if="['pending_approval', 'approved', 'awaiting_payment'].includes(booking.status)"
                  @click="cancelBooking(booking.id)"
                  :disabled="cancellingId === booking.id"
                  class="text-xs text-red-600 hover:text-red-800 font-medium ml-auto"
                >
                  {{ cancellingId === booking.id ? 'Cancelling...' : 'Cancel' }}
                </button>

                <!-- Pay Now button (for approved, awaiting_payment) -->
                <Button
                  v-if="booking.status === 'awaiting_payment'"
                  size="sm"
                  :disabled="payingId === booking.id"
                  @click="initiatePayment(booking.id)"
                  class="text-xs h-7"
                >
                  {{ payingId === booking.id ? '...' : 'Pay Now' }}
                </Button>
              </div>
            </div>
          </div>
        </div>

        <!-- Empty filtered state -->
        <div v-else-if="bookings.length > 0" class="text-center py-12">
          <p class="text-sm text-zinc-500">No bookings with this status.</p>
        </div>
      </template>
    </main>
  </div>
</template>

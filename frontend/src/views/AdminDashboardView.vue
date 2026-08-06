<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { RouterLink } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import Navbar from '@/components/Navbar.vue'
import Button from '@/components/ui/Button.vue'
import api from '@/services/api'
import {
  Clock, CheckCircle, XCircle, Car, AlertCircle, Shield,
  ChevronDown, ChevronUp, User, Search,
} from 'lucide-vue-next'

const auth = useAuthStore()

interface AdminSummary {
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

interface AdminBookingItem {
  id: number
  booking_number: string
  customer: number
  customer_email: string
  customer_name: string
  vehicle: number
  vehicle_name: string
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
const isAdmin = ref(false)
const summary = ref<AdminSummary | null>(null)
const bookings = ref<AdminBookingItem[]>([])
const expandedId = ref<number | null>(null)
const searchQuery = ref('')
const processingId = ref<number | null>(null)
const rejectReason = ref('')
const showRejectDialog = ref<number | null>(null)

const STATUS_TABS = [
  { key: 'all', label: 'All' },
  { key: 'pending_approval', label: 'Pending', highlight: true },
  { key: 'approved', label: 'Approved' },
  { key: 'awaiting_payment', label: 'Awaiting Payment' },
  { key: 'confirmed', label: 'Confirmed' },
  { key: 'active', label: 'Active' },
  { key: 'completed', label: 'Completed' },
  { key: 'cancelled', label: 'Cancelled' },
  { key: 'rejected', label: 'Rejected' },
] as const

const activeTab = ref<string>('pending_approval')

const filteredBookings = computed(() => {
  let result = bookings.value
  if (activeTab.value !== 'all') {
    result = result.filter(b => b.status === activeTab.value)
  }
  if (searchQuery.value.trim()) {
    const q = searchQuery.value.toLowerCase()
    result = result.filter(b =>
      b.booking_number.toLowerCase().includes(q) ||
      b.customer_name.toLowerCase().includes(q) ||
      b.customer_email.toLowerCase().includes(q) ||
      b.vehicle_name.toLowerCase().includes(q)
    )
  }
  return result
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

async function approveBooking(bookingId: number) {
  processingId.value = bookingId
  try {
    await api.post(`/bookings/${bookingId}/approve/`)
    await fetchDashboard()
  } catch {
    // ignore
  } finally {
    processingId.value = null
  }
}

async function rejectBooking(bookingId: number) {
  if (!rejectReason.value.trim()) return
  processingId.value = bookingId
  try {
    await api.post(`/bookings/${bookingId}/reject/`, {
      rejection_reason: rejectReason.value,
    })
    showRejectDialog.value = null
    rejectReason.value = ''
    await fetchDashboard()
  } catch {
    // ignore
  } finally {
    processingId.value = null
  }
}

async function confirmBooking(bookingId: number) {
  processingId.value = bookingId
  try {
    await api.post(`/bookings/${bookingId}/confirm/`)
    await fetchDashboard()
  } catch {
    // ignore
  } finally {
    processingId.value = null
  }
}

async function markActive(bookingId: number) {
  processingId.value = bookingId
  try {
    await api.post(`/bookings/${bookingId}/mark-active/`)
    await fetchDashboard()
  } catch {
    // ignore
  } finally {
    processingId.value = null
  }
}

async function markComplete(bookingId: number) {
  processingId.value = bookingId
  try {
    await api.post(`/bookings/${bookingId}/mark-complete/`)
    await fetchDashboard()
  } catch {
    // ignore
  } finally {
    processingId.value = null
  }
}

async function fetchDashboard() {
  try {
    const response = await api.get('/dashboard/admin/')
    summary.value = response.data.summary
    bookings.value = response.data.bookings
    isAdmin.value = true
  } catch (err: unknown) {
    if ((err as { response?: { status?: number } })?.response?.status === 403) {
      isAdmin.value = false
    }
  }
}

onMounted(async () => {
  try {
    await fetchDashboard()
  } catch {
    error.value = 'Failed to load admin dashboard.'
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="min-h-screen flex flex-col bg-zinc-50">
    <Navbar />

    <main class="flex-1 max-w-6xl mx-auto px-4 pt-24 pb-16 w-full">
      <!-- Header -->
      <div class="flex items-center gap-3 mb-8">
        <div class="h-10 w-10 rounded-full bg-zinc-900 flex items-center justify-center">
          <Shield class="h-5 w-5 text-white" />
        </div>
        <div>
          <h1 class="text-2xl font-semibold text-zinc-900">Admin Dashboard</h1>
          <p class="text-sm text-zinc-500">Manage booking requests and rentals.</p>
        </div>
      </div>

      <!-- Not Admin -->
      <div v-if="!loading && !isAdmin && !error" class="text-center py-20">
        <div class="inline-flex items-center justify-center w-16 h-16 rounded-full bg-zinc-100 mb-4">
          <Shield class="h-8 w-8 text-zinc-400" />
        </div>
        <h2 class="text-lg font-medium text-zinc-900 mb-2">Access Denied</h2>
        <p class="text-sm text-zinc-500">You need administrator privileges to view this page.</p>
      </div>

      <!-- Loading -->
      <div v-else-if="loading" class="text-center py-20">
        <p class="text-sm text-zinc-500">Loading admin dashboard...</p>
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
            <p class="text-xs text-amber-600 mt-1">Pending Review</p>
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
            <p class="text-xs text-emerald-600 mt-1">Active Rentals</p>
          </div>
          <div class="rounded-md border border-zinc-200 bg-zinc-50 p-4">
            <p class="text-2xl font-bold text-zinc-800">{{ summary.total }}</p>
            <p class="text-xs text-zinc-500 mt-1">Total Bookings</p>
          </div>
        </div>

        <!-- Search + Tabs -->
        <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
          <!-- Status Tabs -->
          <div class="flex flex-wrap gap-1.5">
            <button
              v-for="tab in STATUS_TABS"
              :key="tab.key"
              @click="activeTab = tab.key"
              class="px-3 py-1.5 text-xs font-medium rounded-md transition-colors"
              :class="[
                activeTab === tab.key
                  ? (tab.highlight ? 'bg-amber-500 text-white' : 'bg-zinc-900 text-white')
                  : 'bg-white border border-zinc-200 text-zinc-600 hover:bg-zinc-50',
                tab.highlight && activeTab !== tab.key ? 'border-amber-300' : '',
              ]"
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

          <!-- Search -->
          <div class="relative">
            <Search class="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-zinc-400" />
            <input
              v-model="searchQuery"
              type="text"
              placeholder="Search bookings..."
              class="h-9 w-full sm:w-64 rounded-md border border-zinc-300 bg-white pl-9 pr-3 text-sm placeholder:text-zinc-400 focus:outline-none focus:ring-2 focus:ring-zinc-400"
            />
          </div>
        </div>

        <!-- Bookings Table -->
        <div v-if="filteredBookings.length > 0" class="rounded-md border border-zinc-200 bg-white overflow-hidden">
          <div class="overflow-x-auto">
            <table class="w-full text-sm">
              <thead>
                <tr class="border-b border-zinc-200 bg-zinc-50">
                  <th class="text-left px-4 py-3 text-xs font-medium text-zinc-500">Booking #</th>
                  <th class="text-left px-4 py-3 text-xs font-medium text-zinc-500">Customer</th>
                  <th class="text-left px-4 py-3 text-xs font-medium text-zinc-500">Vehicle</th>
                  <th class="text-left px-4 py-3 text-xs font-medium text-zinc-500">Dates</th>
                  <th class="text-left px-4 py-3 text-xs font-medium text-zinc-500">Total</th>
                  <th class="text-left px-4 py-3 text-xs font-medium text-zinc-500">Status</th>
                  <th class="text-right px-4 py-3 text-xs font-medium text-zinc-500">Actions</th>
                </tr>
              </thead>
              <tbody>
                <template v-for="booking in filteredBookings" :key="booking.id">
                  <tr
                    @click="toggleExpanded(booking.id)"
                    class="border-b border-zinc-100 hover:bg-zinc-50 cursor-pointer transition-colors"
                  >
                    <td class="px-4 py-3 font-mono text-xs text-zinc-600">{{ booking.booking_number }}</td>
                    <td class="px-4 py-3">
                      <div class="flex items-center gap-2">
                        <div class="h-7 w-7 rounded-full bg-zinc-200 flex items-center justify-center flex-shrink-0">
                          <User class="h-3.5 w-3.5 text-zinc-500" />
                        </div>
                        <div class="min-w-0">
                          <p class="text-sm font-medium text-zinc-900 truncate">{{ booking.customer_name }}</p>
                          <p class="text-xs text-zinc-400 truncate">{{ booking.customer_email }}</p>
                        </div>
                      </div>
                    </td>
                    <td class="px-4 py-3 text-sm text-zinc-700">{{ booking.vehicle_name }}</td>
                    <td class="px-4 py-3">
                      <p class="text-xs text-zinc-700">{{ formatDate(booking.pickup_date) }}</p>
                      <p class="text-xs text-zinc-400">to {{ formatDate(booking.return_date) }}</p>
                      <p class="text-xs text-zinc-400">{{ booking.rental_days }} day{{ booking.rental_days > 1 ? 's' : '' }}</p>
                    </td>
                    <td class="px-4 py-3 font-medium text-zinc-900">
                      ₱{{ Number(booking.estimated_total).toLocaleString('en-PH') }}
                    </td>
                    <td class="px-4 py-3">
                      <span
                        class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium"
                        :class="statusBadgeClass(booking.status)"
                      >
                        {{ booking.status_display }}
                      </span>
                    </td>
                    <td class="px-4 py-3 text-right" @click.stop>
                      <!-- View Transaction link -->
                      <RouterLink
                        :to="`/admin/transactions/${booking.id}`"
                        class="inline-flex items-center gap-1 text-xs text-zinc-500 hover:text-zinc-900 mr-2"
                      >
                        View
                      </RouterLink>

                      <!-- Pending Approval actions -->
                      <div v-if="booking.status === 'pending_approval'" class="flex items-center justify-end gap-1.5">
                        <Button
                          size="sm"
                          :disabled="processingId === booking.id"
                          @click="approveBooking(booking.id)"
                          class="text-xs h-7"
                        >
                          {{ processingId === booking.id ? '...' : 'Approve' }}
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          :disabled="processingId === booking.id"
                          @click="showRejectDialog = booking.id; rejectReason = ''"
                          class="text-xs h-7 text-red-600 hover:bg-red-50"
                        >
                          Reject
                        </Button>
                      </div>

                      <!-- Awaiting Payment actions -->
                      <Button
                        v-else-if="booking.status === 'awaiting_payment'"
                        size="sm"
                        :disabled="processingId === booking.id"
                        @click="confirmBooking(booking.id)"
                        class="text-xs h-7"
                      >
                        {{ processingId === booking.id ? '...' : 'Confirm' }}
                      </Button>

                      <!-- Confirmed → Mark Active -->
                      <Button
                        v-else-if="booking.status === 'confirmed'"
                        size="sm"
                        :disabled="processingId === booking.id"
                        @click="markActive(booking.id)"
                        class="text-xs h-7"
                      >
                        {{ processingId === booking.id ? '...' : 'Mark Active' }}
                      </Button>

                      <!-- Active → Mark Complete -->
                      <Button
                        v-else-if="booking.status === 'active'"
                        size="sm"
                        :disabled="processingId === booking.id"
                        @click="markComplete(booking.id)"
                        class="text-xs h-7"
                      >
                        {{ processingId === booking.id ? '...' : 'Complete' }}
                      </Button>

                      <!-- Other statuses — no action -->
                      <span v-else class="text-xs text-zinc-400">—</span>
                    </td>
                  </tr>

                  <!-- Reject dialog inline -->
                  <tr v-if="showRejectDialog === booking.id">
                    <td colspan="7" class="px-4 py-3 bg-red-50 border-b border-red-100">
                      <div class="flex items-start gap-3">
                        <div class="flex-1 space-y-2">
                          <p class="text-sm font-medium text-red-800">Reject Booking #{{ booking.booking_number }}</p>
                          <textarea
                            v-model="rejectReason"
                            rows="2"
                            placeholder="Enter reason for rejection..."
                            class="w-full rounded-md border border-red-300 bg-white px-3 py-2 text-sm placeholder:text-zinc-400 focus:outline-none focus:ring-2 focus:ring-red-400"
                          />
                        </div>
                        <div class="flex items-center gap-1.5 pt-5">
                          <Button
                            size="sm"
                            variant="ghost"
                            @click="showRejectDialog = null"
                            class="text-xs h-7"
                          >
                            Cancel
                          </Button>
                          <Button
                            size="sm"
                            :disabled="!rejectReason.trim() || processingId === booking.id"
                            @click="rejectBooking(booking.id)"
                            class="text-xs h-7 bg-red-600 hover:bg-red-700"
                          >
                            {{ processingId === booking.id ? '...' : 'Confirm Reject' }}
                          </Button>
                        </div>
                      </div>
                    </td>
                  </tr>

                  <!-- Expanded detail row -->
                  <tr v-if="expandedId === booking.id" class="bg-zinc-50 border-b border-zinc-100">
                    <td colspan="7" class="px-4 py-4">
                      <div class="grid grid-cols-2 sm:grid-cols-4 gap-4">
                        <div>
                          <p class="text-xs text-zinc-400">Pickup</p>
                          <p class="text-sm text-zinc-900">{{ formatDate(booking.pickup_date) }} at {{ formatTime(booking.pickup_time) }}</p>
                        </div>
                        <div>
                          <p class="text-xs text-zinc-400">Return</p>
                          <p class="text-sm text-zinc-900">{{ formatDate(booking.return_date) }} at {{ formatTime(booking.return_time) }}</p>
                        </div>
                        <div>
                          <p class="text-xs text-zinc-400">Subtotal</p>
                          <p class="text-sm text-zinc-900">₱{{ Number(booking.subtotal).toLocaleString('en-PH') }}</p>
                        </div>
                        <div>
                          <p class="text-xs text-zinc-400">Created</p>
                          <p class="text-sm text-zinc-900">{{ formatDate(booking.created_at) }}</p>
                        </div>
                      </div>

                      <div v-if="booking.special_request" class="mt-3">
                        <p class="text-xs text-zinc-400">Special Request</p>
                        <p class="text-sm text-zinc-700">{{ booking.special_request }}</p>
                      </div>

                      <div v-if="booking.rejection_reason" class="mt-3 rounded-md bg-red-50 border border-red-200 p-3">
                        <p class="text-xs font-medium text-red-800 mb-0.5">Rejection Reason</p>
                        <p class="text-sm text-red-700">{{ booking.rejection_reason }}</p>
                      </div>
                    </td>
                  </tr>
                </template>
              </tbody>
            </table>
          </div>
        </div>

        <!-- Empty state -->
        <div v-else class="text-center py-16">
          <div class="inline-flex items-center justify-center w-16 h-16 rounded-full bg-zinc-100 mb-4">
            <Car class="h-8 w-8 text-zinc-400" />
          </div>
          <h2 class="text-lg font-medium text-zinc-900 mb-2">No bookings found</h2>
          <p class="text-sm text-zinc-500">
            {{ searchQuery ? 'Try a different search term.' : 'No bookings match this status.' }}
          </p>
        </div>
      </template>
    </main>
  </div>
</template>

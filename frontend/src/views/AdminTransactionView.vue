<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, RouterLink } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import Navbar from '@/components/Navbar.vue'
import Button from '@/components/ui/Button.vue'
import api from '@/services/api'
import {
  ChevronLeft, Check, Clock, XCircle, AlertCircle,
  CreditCard, Car, CheckCircle, Calendar, Shield, User,
} from 'lucide-vue-next'

const route = useRoute()
const auth = useAuthStore()

interface Booking {
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

const booking = ref<Booking | null>(null)
const loading = ref(true)
const error = ref('')
const processing = ref(false)
const rejectReason = ref('')
const showRejectDialog = ref(false)

const STEPS = [
  { key: 'request', label: 'Request', icon: Clock },
  { key: 'review', label: 'Review', icon: AlertCircle },
  { key: 'payment', label: 'Payment', icon: CreditCard },
  { key: 'pickup', label: 'For Pickup', icon: Car },
  { key: 'active', label: 'Active', icon: Car },
  { key: 'returned', label: 'Returned', icon: Calendar },
  { key: 'complete', label: 'Complete', icon: CheckCircle },
]

function currentStepIndex(status: string): number {
  switch (status) {
    case 'pending_approval': return 1
    case 'approved': return 2
    case 'awaiting_payment': return 2
    case 'confirmed': return 3
    case 'active': return 4
    case 'completed': return 6
    case 'rejected': return 1
    case 'cancelled': return -1
    default: return 0
  }
}

function stepState(stepIndex: number, currentIdx: number, status: string): 'done' | 'current' | 'upcoming' | 'rejected' | 'cancelled' {
  if (status === 'cancelled') return stepIndex <= 1 ? (stepIndex === 1 ? 'cancelled' : 'done') : 'upcoming'
  if (status === 'rejected' && stepIndex === 1) return 'rejected'
  if (stepIndex < currentIdx) return 'done'
  if (stepIndex === currentIdx) return 'current'
  return 'upcoming'
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

async function approveBooking() {
  if (!booking.value) return
  processing.value = true
  try {
    await api.post(`/bookings/${booking.value.id}/approve/`)
    await fetchBooking()
  } finally { processing.value = false }
}

async function rejectBooking() {
  if (!booking.value || !rejectReason.value.trim()) return
  processing.value = true
  try {
    await api.post(`/bookings/${booking.value.id}/reject/`, { rejection_reason: rejectReason.value })
    showRejectDialog.value = false
    rejectReason.value = ''
    await fetchBooking()
  } finally { processing.value = false }
}

async function confirmPayment() {
  if (!booking.value) return
  processing.value = true
  try {
    await api.post(`/bookings/${booking.value.id}/confirm/`)
    await fetchBooking()
  } finally { processing.value = false }
}

async function markActive() {
  if (!booking.value) return
  processing.value = true
  try {
    await api.post(`/bookings/${booking.value.id}/mark-active/`)
    await fetchBooking()
  } finally { processing.value = false }
}

async function completeTransaction() {
  if (!booking.value) return
  processing.value = true
  try {
    await api.post(`/bookings/${booking.value.id}/mark-complete/`)
    await fetchBooking()
  } finally { processing.value = false }
}

async function fetchBooking() {
  try {
    const response = await api.get(`/bookings/${route.params.id}/`)
    if (response.data.customer !== auth.user?.id && !auth.user?.is_staff) {
      error.value = 'Not authorized.'
    } else {
      booking.value = response.data
    }
  } catch {
    error.value = 'Booking not found.'
  } finally {
    loading.value = false
  }
}

const currentIdx = computed(() => booking.value ? currentStepIndex(booking.value.status) : 0)
const stepHint = computed(() => {
  if (!booking.value) return ''
  switch (booking.value.status) {
    case 'pending_approval': return 'Awaiting your review'
    case 'approved': return 'Customer needs to pay'
    case 'awaiting_payment': return 'Awaiting payment confirmation'
    case 'confirmed': return 'Ready for pickup'
    case 'active': return 'Vehicle is currently rented'
    case 'completed': return 'Transaction complete'
    case 'rejected': return `Rejected: ${booking.value.rejection_reason || 'No reason'}`
    case 'cancelled': return 'Cancelled by customer'
    default: return ''
  }
})

onMounted(fetchBooking)
</script>

<template>
  <div class="min-h-screen flex flex-col bg-zinc-50">
    <Navbar />

    <main class="flex-1 max-w-6xl mx-auto px-4 pt-24 pb-16 w-full">
      <!-- Loading -->
      <div v-if="loading" class="text-center py-20">
        <p class="text-sm text-zinc-500">Loading transaction...</p>
      </div>

      <!-- Error -->
      <div v-else-if="error" class="text-center py-20">
        <p class="text-sm text-zinc-500">{{ error }}</p>
        <RouterLink to="/admin/dashboard" class="text-sm text-zinc-900 font-medium hover:underline mt-2 inline-block">
          Back to Admin Dashboard
        </RouterLink>
      </div>

      <template v-else-if="booking">
        <!-- Back -->
        <RouterLink to="/admin/dashboard" class="inline-flex items-center gap-1 text-sm text-zinc-500 hover:text-zinc-900 mb-6">
          <ChevronLeft class="h-4 w-4" /> Back to Admin Dashboard
        </RouterLink>

        <div class="flex items-center gap-3 mb-8">
          <div class="h-10 w-10 rounded-full bg-zinc-900 flex items-center justify-center">
            <Shield class="h-5 w-5 text-white" />
          </div>
          <div>
            <h1 class="text-2xl font-semibold text-zinc-900">Transaction Details</h1>
            <p class="text-sm text-zinc-500">{{ booking.booking_number }}</p>
          </div>
        </div>

        <!-- Progress Steps -->
        <div class="rounded-md border border-zinc-200 bg-white p-6 mb-8">
          <div class="flex items-start justify-between overflow-x-auto gap-2">
            <div
              v-for="(step, idx) in STEPS"
              :key="step.key"
              class="flex flex-col items-center min-w-[60px] flex-shrink-0"
              :class="idx > 0 ? 'flex-1' : ''"
            >
              <div v-if="idx > 0" class="w-full h-0.5 -mt-0.5 mb-2" :class="{
                'bg-zinc-900': stepState(idx, currentIdx, booking.status) === 'done',
                'bg-zinc-200': stepState(idx, currentIdx, booking.status) === 'upcoming',
                'bg-zinc-300': stepState(idx, currentIdx, booking.status) === 'current',
                'bg-red-300': stepState(idx, currentIdx, booking.status) === 'rejected' || stepState(idx, currentIdx, booking.status) === 'cancelled',
              }" />
              <div
                class="h-8 w-8 rounded-full flex items-center justify-center text-xs font-medium"
                :class="{
                  'bg-zinc-900 text-white': stepState(idx, currentIdx, booking.status) === 'done' || stepState(idx, currentIdx, booking.status) === 'current',
                  'bg-zinc-100 text-zinc-400': stepState(idx, currentIdx, booking.status) === 'upcoming',
                  'bg-red-100 text-red-600': stepState(idx, currentIdx, booking.status) === 'rejected',
                  'bg-zinc-200 text-zinc-500 line-through': stepState(idx, currentIdx, booking.status) === 'cancelled',
                }"
              >
                <Check v-if="stepState(idx, currentIdx, booking.status) === 'done'" class="h-4 w-4" />
                <XCircle v-else-if="stepState(idx, currentIdx, booking.status) === 'rejected' || stepState(idx, currentIdx, booking.status) === 'cancelled'" class="h-4 w-4" />
                <component :is="step.icon" v-else class="h-4 w-4" />
              </div>
              <span class="text-[10px] text-zinc-500 mt-1 text-center leading-tight">{{ step.label }}</span>
            </div>
          </div>
          <p class="text-xs text-zinc-500 text-center mt-4">{{ stepHint }}</p>
        </div>

        <!-- Two-column layout -->
        <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
          <!-- Left: Booking Details -->
          <div class="lg:col-span-2 space-y-6">
            <!-- Customer Info -->
            <div class="rounded-md border border-zinc-200 bg-white p-6">
              <h2 class="text-sm font-semibold text-zinc-900 mb-4">Customer</h2>
              <div class="flex items-center gap-3">
                <div class="h-10 w-10 rounded-full bg-zinc-200 flex items-center justify-center">
                  <User class="h-5 w-5 text-zinc-500" />
                </div>
                <div>
                  <p class="text-sm font-medium text-zinc-900">{{ booking.customer_name }}</p>
                  <p class="text-xs text-zinc-500">{{ booking.customer_email }}</p>
                </div>
              </div>
            </div>

            <!-- Booking Details -->
            <div class="rounded-md border border-zinc-200 bg-white p-6">
              <h2 class="text-sm font-semibold text-zinc-900 mb-4">Booking Details</h2>
              <div class="grid grid-cols-2 gap-4 mb-6">
                <div>
                  <p class="text-xs text-zinc-400">Transaction ID</p>
                  <p class="text-sm font-mono text-zinc-900">{{ booking.booking_number }}</p>
                </div>
                <div>
                  <p class="text-xs text-zinc-400">Status</p>
                  <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium"
                    :class="{
                      'bg-amber-100 text-amber-800': booking.status === 'pending_approval',
                      'bg-blue-100 text-blue-800': booking.status === 'approved',
                      'bg-purple-100 text-purple-800': booking.status === 'awaiting_payment',
                      'bg-green-100 text-green-800': booking.status === 'confirmed',
                      'bg-emerald-100 text-emerald-800': booking.status === 'active',
                      'bg-zinc-100 text-zinc-800': booking.status === 'completed',
                      'bg-red-100 text-red-800': ['cancelled', 'rejected'].includes(booking.status),
                    }"
                  >
                    {{ booking.status_display }}
                  </span>
                </div>
                <div>
                  <p class="text-xs text-zinc-400">Created</p>
                  <p class="text-sm text-zinc-900">{{ formatDate(booking.created_at) }}</p>
                </div>
                <div>
                  <p class="text-xs text-zinc-400">Last Updated</p>
                  <p class="text-sm text-zinc-900">{{ formatDate(booking.updated_at) }}</p>
                </div>
              </div>

              <!-- Vehicle info -->
              <div class="flex items-center gap-4 p-4 rounded-md bg-zinc-50 border border-zinc-100 mb-6">
                <div class="h-16 w-24 rounded bg-zinc-200 overflow-hidden flex-shrink-0">
                  <div class="h-full w-full flex items-center justify-center">
                    <Car class="h-6 w-6 text-zinc-400" />
                  </div>
                </div>
                <div>
                  <p class="text-sm font-medium text-zinc-900">{{ booking.vehicle_name }}</p>
                  <RouterLink :to="`/vehicles/${booking.vehicle}`" class="text-xs text-zinc-500 hover:text-zinc-900">
                    View Vehicle
                  </RouterLink>
                </div>
              </div>

              <!-- Dates -->
              <div class="grid grid-cols-2 gap-4 mb-4">
                <div class="flex items-start gap-2">
                  <Calendar class="h-4 w-4 text-zinc-400 mt-0.5 flex-shrink-0" />
                  <div>
                    <p class="text-xs text-zinc-500">Pickup</p>
                    <p class="text-sm font-medium text-zinc-900">{{ formatDate(booking.pickup_date) }}</p>
                    <p class="text-xs text-zinc-400">{{ formatTime(booking.pickup_time) }}</p>
                  </div>
                </div>
                <div class="flex items-start gap-2">
                  <Calendar class="h-4 w-4 text-zinc-400 mt-0.5 flex-shrink-0" />
                  <div>
                    <p class="text-xs text-zinc-500">Return</p>
                    <p class="text-sm font-medium text-zinc-900">{{ formatDate(booking.return_date) }}</p>
                    <p class="text-xs text-zinc-400">{{ formatTime(booking.return_time) }}</p>
                  </div>
                </div>
              </div>

              <div v-if="booking.special_request" class="pt-4 border-t border-zinc-100">
                <p class="text-xs text-zinc-400 mb-1">Special Request</p>
                <p class="text-sm text-zinc-700">{{ booking.special_request }}</p>
              </div>

              <div v-if="booking.rejection_reason" class="mt-4 rounded-md bg-red-50 border border-red-200 p-3">
                <p class="text-xs font-medium text-red-800 mb-0.5">Rejection Reason</p>
                <p class="text-sm text-red-700">{{ booking.rejection_reason }}</p>
              </div>
            </div>

            <!-- Cost Summary -->
            <div class="rounded-md border border-zinc-200 bg-white p-6">
              <h2 class="text-sm font-semibold text-zinc-900 mb-4">Cost Summary</h2>
              <div class="space-y-2">
                <div class="flex justify-between text-sm">
                  <span class="text-zinc-500">Rental Days</span>
                  <span class="text-zinc-900">{{ booking.rental_days }} day{{ booking.rental_days > 1 ? 's' : '' }}</span>
                </div>
                <div class="flex justify-between text-sm">
                  <span class="text-zinc-500">Subtotal</span>
                  <span class="text-zinc-900">₱{{ Number(booking.subtotal).toLocaleString('en-PH') }}</span>
                </div>
                <hr class="border-zinc-200" />
                <div class="flex justify-between text-sm font-semibold">
                  <span class="text-zinc-900">Estimated Total</span>
                  <span class="text-zinc-900">₱{{ Number(booking.estimated_total).toLocaleString('en-PH') }}</span>
                </div>
              </div>
            </div>
          </div>

          <!-- Right: Admin Actions -->
          <div>
            <div class="rounded-md border border-zinc-200 bg-white p-6 space-y-4 sticky top-24">
              <h2 class="text-sm font-semibold text-zinc-900">Actions</h2>

              <!-- Pending: Approve / Reject -->
              <template v-if="booking.status === 'pending_approval'">
                <Button
                  class="w-full"
                  :disabled="processing"
                  @click="approveBooking"
                >
                  {{ processing ? '...' : 'Approve Booking' }}
                </Button>
                <Button
                  variant="ghost"
                  class="w-full text-red-600 hover:bg-red-50"
                  :disabled="processing"
                  @click="showRejectDialog = true; rejectReason = ''"
                >
                  Reject Booking
                </Button>

                <!-- Reject Dialog -->
                <div v-if="showRejectDialog" class="space-y-3 pt-2 border-t border-zinc-100">
                  <p class="text-sm font-medium text-red-800">Rejection Reason</p>
                  <textarea
                    v-model="rejectReason"
                    rows="2"
                    placeholder="Enter reason..."
                    class="w-full rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm placeholder:text-zinc-400 focus:outline-none focus:ring-2 focus:ring-zinc-400"
                  />
                  <div class="flex gap-2">
                    <Button
                      size="sm"
                      variant="ghost"
                      class="flex-1"
                      @click="showRejectDialog = false"
                    >
                      Cancel
                    </Button>
                    <Button
                      size="sm"
                      class="flex-1 bg-red-600 hover:bg-red-700"
                      :disabled="!rejectReason.trim() || processing"
                      @click="rejectBooking"
                    >
                      {{ processing ? '...' : 'Confirm Reject' }}
                    </Button>
                  </div>
                </div>
              </template>

              <!-- Awaiting Payment: Confirm Payment -->
              <template v-else-if="booking.status === 'awaiting_payment'">
                <Button
                  class="w-full"
                  :disabled="processing"
                  @click="confirmPayment"
                >
                  {{ processing ? '...' : 'Confirm Payment' }}
                </Button>
              </template>

              <!-- Confirmed: Mark Active -->
              <template v-else-if="booking.status === 'confirmed'">
                <Button
                  class="w-full"
                  :disabled="processing"
                  @click="markActive"
                >
                  {{ processing ? '...' : 'Mark as Active' }}
                </Button>
              </template>

              <!-- Active: Complete -->
              <template v-else-if="booking.status === 'active'">
                <Button
                  class="w-full"
                  :disabled="processing"
                  @click="completeTransaction"
                >
                  {{ processing ? '...' : 'Complete Transaction' }}
                </Button>
              </template>

              <!-- Completed -->
              <template v-else-if="booking.status === 'completed'">
                <div class="text-center">
                  <CheckCircle class="h-8 w-8 text-green-500 mx-auto mb-2" />
                  <p class="text-xs text-green-700 font-medium">Transaction Complete</p>
                </div>
              </template>

              <!-- Rejected / Cancelled -->
              <template v-else-if="booking.status === 'rejected'">
                <div class="text-center">
                  <XCircle class="h-8 w-8 text-red-400 mx-auto mb-2" />
                  <p class="text-xs text-red-600 font-medium">Booking Rejected</p>
                </div>
              </template>
              <template v-else-if="booking.status === 'cancelled'">
                <div class="text-center">
                  <XCircle class="h-8 w-8 text-zinc-400 mx-auto mb-2" />
                  <p class="text-xs text-zinc-500 font-medium">Cancelled by Customer</p>
                </div>
              </template>
            </div>
          </div>
        </div>
      </template>
    </main>
  </div>
</template>

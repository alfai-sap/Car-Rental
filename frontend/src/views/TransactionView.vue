<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, RouterLink } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import Navbar from '@/components/Navbar.vue'
import Button from '@/components/ui/Button.vue'
import api from '@/services/api'
import {
  ChevronLeft, Check, Clock, XCircle, AlertCircle,
  CreditCard, Car, CheckCircle, Calendar,
} from 'lucide-vue-next'

interface IdentityDoc {
  id: number
  document_type: string
  document_number: string
  front_image: string | null
  back_image: string | null
}

interface VehicleImage {
  id: number
  image: string
  is_primary: boolean
}

interface Booking {
  id: number
  booking_number: string
  customer: number
  customer_email: string
  customer_name: string
  customer_phone: string
  customer_identity_docs: IdentityDoc[]
  vehicle: number
  vehicle_name: string
  vehicle_images: VehicleImage[]
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

const route = useRoute()
const auth = useAuthStore()

const booking = ref<Booking | null>(null)
const loading = ref(true)
const error = ref('')
const cancelling = ref(false)
const paying = ref(false)
const lightboxImage = ref('')

// ── Cancel modal state ──
const showCancelModal = ref(false)
const cancelReasonType = ref('')
const cancelReasonCustom = ref('')
const CANCEL_REASONS = [
  { value: '', label: 'Select a reason...' },
  { value: 'change_of_mind', label: 'Changed my mind' },
  { value: 'found_better_price', label: 'Found a better price elsewhere' },
  { value: 'date_change', label: 'Need to change rental dates' },
  { value: 'vehicle_choice', label: 'Want to book a different vehicle' },
  { value: 'travel_cancelled', label: 'Travel plans cancelled' },
  { value: 'other', label: 'Other — specify below' },
]

function openCancelModal() {
  cancelReasonType.value = ''
  cancelReasonCustom.value = ''
  showCancelModal.value = true
}

function closeCancelModal() {
  showCancelModal.value = false
}

const cancelReasonText = computed(() => {
  if (cancelReasonType.value === 'other') return cancelReasonCustom.value
  const found = CANCEL_REASONS.find(r => r.value === cancelReasonType.value)
  return found && found.value ? found.label : ''
})

const canConfirmCancel = computed(() => {
  if (!cancelReasonType.value) return false
  if (cancelReasonType.value === 'other') return cancelReasonCustom.value.trim().length > 0
  return true
})

async function confirmCancel() {
  if (!booking.value || !canConfirmCancel.value) return
  cancelling.value = true
  try {
    await api.post(`/bookings/${booking.value.id}/cancel/`, {
      cancellation_reason: cancelReasonText.value,
    })
    showCancelModal.value = false
    await fetchBooking()
  } catch { /* ignore */ }
  finally { cancelling.value = false }
}

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
  if (!dateStr) return '—'
  if (dateStr.includes('T')) return new Date(dateStr).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
  return new Date(dateStr + 'T00:00:00').toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}

function formatDateTime(dateStr: string): string {
  if (!dateStr) return '—'
  const d = new Date(dateStr)
  if (isNaN(d.getTime())) return '—'
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric', hour: 'numeric', minute: '2-digit' })
}

function formatTime(timeStr: string): string {
  const [h, m] = timeStr.split(':')
  const hour = parseInt(h)
  const ampm = hour >= 12 ? 'PM' : 'AM'
  const display = hour > 12 ? hour - 12 : hour === 0 ? 12 : hour
  return `${display}:${m} ${ampm}`
}

async function initiatePayment() {
  if (!booking.value) return
  paying.value = true
  try {
    const response = await api.post('/payments/create-session/', { booking_id: booking.value.id })
    if (response.data.checkout_url) window.location.href = response.data.checkout_url
  } catch { /* ignore */ }
  finally { paying.value = false }
}

async function fetchBooking() {
  try {
    const response = await api.get(`/bookings/${route.params.id}/`)
    booking.value = response.data
    if (booking.value && booking.value.customer !== auth.user?.id && !auth.user?.is_staff) {
      error.value = 'Not authorized.'
      booking.value = null
    }
  } catch { error.value = 'Booking not found.' }
  finally { loading.value = false }
}

const currentIdx = computed(() => booking.value ? currentStepIndex(booking.value.status) : 0)
const canCancel = computed(() => {
  if (!booking.value) return false
  return ['pending_approval', 'approved', 'awaiting_payment'].includes(booking.value.status)
})
const canPay = computed(() => booking.value?.status === 'awaiting_payment')
const stepHint = computed(() => {
  if (!booking.value) return ''
  switch (booking.value.status) {
    case 'pending_approval': return 'Waiting for admin review'
    case 'approved': return 'Booking approved — proceed to payment'
    case 'awaiting_payment': return 'Payment required to confirm booking'
    case 'confirmed': return 'Your booking is confirmed — prepare for pickup'
    case 'active': return 'Vehicle is currently rented'
    case 'completed': return 'Rental completed'
    case 'rejected': return `Rejected: ${booking.value.rejection_reason || 'No reason provided'}`
    case 'cancelled': return 'Booking was cancelled'
    default: return ''
  }
})

onMounted(fetchBooking)
</script>

<template>
  <div class="min-h-screen flex flex-col bg-zinc-50">
    <Navbar />
    <main class="flex-1 max-w-6xl mx-auto px-4 pt-24 pb-16 w-full">
      <div v-if="loading" class="text-center py-20"><p class="text-sm text-zinc-500">Loading transaction...</p></div>
      <div v-else-if="error" class="text-center py-20">
        <p class="text-sm text-zinc-500">{{ error }}</p>
        <RouterLink to="/dashboard" class="text-sm text-zinc-900 font-medium hover:underline mt-2 inline-block">Back to Dashboard</RouterLink>
      </div>
      <template v-else-if="booking">
        <RouterLink to="/dashboard" class="inline-flex items-center gap-1 text-sm text-zinc-500 hover:text-zinc-900 mb-6">
          <ChevronLeft class="h-4 w-4" /> Back to Dashboard
        </RouterLink>
        <h1 class="text-2xl font-semibold text-zinc-900 mb-2">Transaction Details</h1>
        <p class="text-sm text-zinc-500 mb-8">{{ booking.booking_number }}</p>

        <!-- Progress Steps -->
        <div class="rounded-md border border-zinc-200 bg-white p-6 mb-8 overflow-x-auto">
          <div class="flex items-center min-w-[600px]">
            <template v-for="(step, idx) in STEPS" :key="step.key">
              <div class="flex flex-col items-center" style="width:60px;flex-shrink:0">
                <div class="h-8 w-8 rounded-full flex items-center justify-center text-xs font-medium" :class="{
                  'bg-zinc-900 text-white': stepState(idx, currentIdx, booking.status) === 'done' || stepState(idx, currentIdx, booking.status) === 'current',
                  'bg-zinc-100 text-zinc-400': stepState(idx, currentIdx, booking.status) === 'upcoming',
                  'bg-red-100 text-red-600': stepState(idx, currentIdx, booking.status) === 'rejected',
                  'bg-zinc-200 text-zinc-500 line-through': stepState(idx, currentIdx, booking.status) === 'cancelled',
                }">
                  <Check v-if="stepState(idx, currentIdx, booking.status) === 'done'" class="h-4 w-4" />
                  <XCircle v-else-if="stepState(idx, currentIdx, booking.status) === 'rejected' || stepState(idx, currentIdx, booking.status) === 'cancelled'" class="h-4 w-4" />
                  <component :is="step.icon" v-else class="h-4 w-4" />
                </div>
                <span class="text-[10px] text-zinc-500 mt-1 text-center leading-tight">{{ step.label }}</span>
              </div>
              <div v-if="idx < STEPS.length - 1" class="flex-1 h-0.5 mx-1" :class="{
                'bg-zinc-900': stepState(idx + 1, currentIdx, booking.status) === 'done',
                'bg-zinc-200': stepState(idx + 1, currentIdx, booking.status) === 'upcoming' || stepState(idx + 1, currentIdx, booking.status) === 'current',
                'bg-red-300': stepState(idx + 1, currentIdx, booking.status) === 'rejected' || stepState(idx + 1, currentIdx, booking.status) === 'cancelled',
              }" />
            </template>
          </div>
          <p class="text-xs text-zinc-500 text-center mt-4">{{ stepHint }}</p>
        </div>

        <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
          <!-- LEFT COLUMN -->
          <div class="lg:col-span-2 space-y-6">
            <div class="rounded-md border border-zinc-200 bg-white p-6">
              <h2 class="text-sm font-semibold text-zinc-900 mb-4">Booking Details</h2>
              <div class="grid grid-cols-2 gap-4 mb-6">
                <div><p class="text-xs text-zinc-400">Transaction ID</p><p class="text-sm font-mono text-zinc-900">{{ booking.booking_number }}</p></div>
                <div><p class="text-xs text-zinc-400">Status</p>
                  <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium" :class="{
                    'bg-amber-100 text-amber-800': booking.status === 'pending_approval',
                    'bg-blue-100 text-blue-800': booking.status === 'approved',
                    'bg-purple-100 text-purple-800': booking.status === 'awaiting_payment',
                    'bg-green-100 text-green-800': booking.status === 'confirmed',
                    'bg-emerald-100 text-emerald-800': booking.status === 'active',
                    'bg-zinc-100 text-zinc-800': booking.status === 'completed',
                    'bg-red-100 text-red-800': ['cancelled','rejected'].includes(booking.status),
                  }">{{ booking.status_display }}</span>
                </div>
                <div><p class="text-xs text-zinc-400">Request Created</p><p class="text-sm text-zinc-900">{{ formatDateTime(booking.created_at) }}</p></div>
                <div><p class="text-xs text-zinc-400">Last Updated</p><p class="text-sm text-zinc-900">{{ formatDateTime(booking.updated_at) }}</p></div>
              </div>
              <div class="p-4 rounded-md bg-zinc-50 border border-zinc-100 mb-6">
                <p class="text-xs font-medium text-zinc-500 uppercase tracking-wider mb-3">Vehicle</p>
                <div class="grid grid-cols-2 sm:grid-cols-3 gap-2">
                  <img v-for="img in (booking.vehicle_images || [])" :key="img.id" :src="img.image" :alt="booking.vehicle_name" class="w-full h-20 object-cover rounded cursor-pointer hover:opacity-80 transition" @click="lightboxImage = img.image" />
                </div>
                <p class="text-sm font-medium text-zinc-900 mt-2">{{ booking.vehicle_name }}</p>
              </div>
              <div class="grid grid-cols-2 gap-4">
                <div class="flex items-start gap-2"><Calendar class="h-4 w-4 text-zinc-400 mt-0.5 flex-shrink-0" /><div><p class="text-xs text-zinc-500">Pickup</p><p class="text-sm font-medium text-zinc-900">{{ formatDate(booking.pickup_date) }}</p><p class="text-xs text-zinc-400">{{ formatTime(booking.pickup_time) }}</p></div></div>
                <div class="flex items-start gap-2"><Calendar class="h-4 w-4 text-zinc-400 mt-0.5 flex-shrink-0" /><div><p class="text-xs text-zinc-500">Return</p><p class="text-sm font-medium text-zinc-900">{{ formatDate(booking.return_date) }}</p><p class="text-xs text-zinc-400">{{ formatTime(booking.return_time) }}</p></div></div>
              </div>
              <div v-if="booking.special_request" class="mt-4 pt-4 border-t border-zinc-100"><p class="text-xs text-zinc-400 mb-1">Special Request</p><p class="text-sm text-zinc-700">{{ booking.special_request }}</p></div>
              <div v-if="booking.rejection_reason" class="mt-4 rounded-md bg-red-50 border border-red-200 p-3"><p class="text-xs font-medium text-red-800 mb-0.5">Cancellation Reason</p><p class="text-sm text-red-700">{{ booking.rejection_reason }}</p></div>
            </div>
            <div class="rounded-md border border-zinc-200 bg-white p-6">
              <h2 class="text-sm font-semibold text-zinc-900 mb-4">Cost Summary</h2>
              <div class="space-y-2">
                <div class="flex justify-between text-sm"><span class="text-zinc-500">Daily Rate</span><span class="text-zinc-900">₱{{ Number(booking.subtotal / booking.rental_days).toLocaleString('en-PH') }}</span></div>
                <div class="flex justify-between text-sm"><span class="text-zinc-500">Rental Days</span><span class="text-zinc-900">{{ booking.rental_days }} day{{ booking.rental_days > 1 ? 's' : '' }}</span></div>
                <div class="flex justify-between text-sm"><span class="text-zinc-500">Subtotal</span><span class="text-zinc-900">₱{{ Number(booking.subtotal).toLocaleString('en-PH') }}</span></div>
                <hr class="border-zinc-200" />
                <div class="flex justify-between text-sm font-semibold"><span class="text-zinc-900">Estimated Total</span><span class="text-zinc-900">₱{{ Number(booking.estimated_total).toLocaleString('en-PH') }}</span></div>
              </div>
            </div>
          </div>
          <!-- RIGHT COLUMN -->
          <div>
            <div class="rounded-md border border-zinc-200 bg-white p-6 space-y-4 sticky top-24">
              <h2 class="text-sm font-semibold text-zinc-900">Payment</h2>
              <div class="rounded-md bg-zinc-50 border border-zinc-100 p-4 text-center">
                <CreditCard class="h-8 w-8 text-zinc-300 mx-auto mb-2" />
                <p class="text-xs text-zinc-500">
                  <template v-if="booking.status === 'awaiting_payment'">Payment is required to confirm your booking.</template>
                  <template v-else-if="booking.status === 'confirmed' || booking.status === 'active' || booking.status === 'completed'">Payment confirmed</template>
                  <template v-else-if="booking.status === 'pending_approval'">Awaiting approval before payment</template>
                  <template v-else>No payment information available</template>
                </p>
              </div>
              <Button v-if="canPay" class="w-full" :disabled="paying" @click="initiatePayment">{{ paying ? 'Redirecting...' : 'Pay Now' }}</Button>
              <Button v-if="canCancel" variant="ghost" class="w-full text-red-600 hover:bg-red-50" :disabled="cancelling" @click="openCancelModal">{{ cancelling ? 'Cancelling...' : 'Cancel Request' }}</Button>
              <div v-if="booking.status === 'completed'" class="text-center"><CheckCircle class="h-8 w-8 text-green-500 mx-auto mb-2" /><p class="text-xs text-green-700 font-medium">Rental Complete</p></div>
            </div>
          </div>
        </div>
        <Teleport to="body">
          <div v-if="lightboxImage" class="fixed inset-0 z-[100] bg-black/90 flex items-center justify-center" @click="lightboxImage = ''">
            <button @click="lightboxImage = ''" class="absolute top-4 right-4 text-white/70 hover:text-white"><XCircle class="h-6 w-6" /></button>
            <img :src="lightboxImage" class="max-w-[90vw] max-h-[85vh] object-contain" />
          </div>
        </Teleport>

        <!-- Cancel Confirmation Modal -->
        <Teleport to="body">
          <div v-if="showCancelModal" class="fixed inset-0 z-[200] flex items-center justify-center p-4">
            <div class="absolute inset-0 bg-black/50" @click="closeCancelModal" />
            <div class="relative bg-white rounded-lg shadow-xl max-w-md w-full p-6 space-y-4">
              <h3 class="text-lg font-semibold text-zinc-900">Cancel Booking Request</h3>
              <p class="text-sm text-zinc-500">Please provide a reason for cancelling your booking request.</p>

              <!-- Reason dropdown -->
              <div class="space-y-1">
                <label class="text-xs font-medium text-zinc-700">Reason</label>
                <select
                  v-model="cancelReasonType"
                  class="h-9 w-full rounded-md border border-zinc-300 bg-white px-3 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-zinc-400"
                  :disabled="cancelling"
                >
                  <option v-for="reason in CANCEL_REASONS" :key="reason.value" :value="reason.value">{{ reason.label }}</option>
                </select>
              </div>

              <!-- Custom reason textarea -->
              <div v-if="cancelReasonType === 'other'" class="space-y-1">
                <label class="text-xs font-medium text-zinc-700">Please specify</label>
                <textarea
                  v-model="cancelReasonCustom"
                  rows="2"
                  placeholder="Enter your reason..."
                  class="w-full rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm placeholder:text-zinc-400 focus:outline-none focus:ring-2 focus:ring-zinc-400"
                  :disabled="cancelling"
                />
              </div>

              <div class="flex gap-2 pt-2">
                <Button variant="ghost" class="flex-1" @click="closeCancelModal" :disabled="cancelling">Back</Button>
                <Button
                  class="flex-1 bg-red-600 hover:bg-red-700 text-white"
                  :disabled="!canConfirmCancel || cancelling"
                  @click="confirmCancel"
                >
                  {{ cancelling ? 'Cancelling...' : 'Confirm Cancellation' }}
                </Button>
              </div>
            </div>
          </div>
        </Teleport>
      </template>
    </main>
  </div>
</template>

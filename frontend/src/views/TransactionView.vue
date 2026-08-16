<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, RouterLink } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import Navbar from '@/components/Navbar.vue'
import Button from '@/components/ui/Button.vue'
import api from '@/services/api'
import {
  ChevronLeft, Check, Clock, XCircle, AlertCircle,
  CreditCard, Car, CheckCircle, Calendar, RefreshCw,
} from 'lucide-vue-next'

interface IdentityDoc {
  id: number
  document_type: string
  document_number: string
  front_image: string | null
  back_image: string | null
}

interface IdentitySnapshotDoc {
  id: number
  document_type: string
  document_number: string
  front_image: string | null
  back_image: string | null
  index?: number
}

interface IdentitySnapshot {
  customer_name: string
  customer_email: string
  customer_phone: string
  documents: IdentitySnapshotDoc[]
  captured_at: string
}

interface VehicleImage {
  id: number
  image: string
  is_primary: boolean
}

interface AssignmentEntry {
  id: number
  previous_plate: string | null
  new_plate: string
  reason: string
  changed_by_name: string
  created_at: string
}

interface PaymentRecord {
  id: number
  payment_number: string
  amount: string
  currency: string
  payment_status: string
  payment_method: string
  paid_at: string | null
  created_at: string
}

interface InvoiceRecord {
  id: number
  invoice_number: string
  subtotal: string
  discount: string
  total: string
  invoice_status: string
  due_date: string | null
}

interface Booking {
  id: number
  hash_id: string
  vehicle_hash_id: string
  booking_number: string
  customer: number
  customer_email: string
  customer_name: string
  customer_phone: string
  customer_identity_docs: IdentityDoc[]
  identity_snapshot: IdentitySnapshot
  vehicle: number
  vehicle_name: string
  vehicle_images: VehicleImage[]
  vehicle_unit: number | null
  vehicle_unit_plate: string | null
  vehicle_unit_status: string | null
  assigned_by: string | null
  pickup_date: string
  return_date: string
  pickup_time: string
  return_time: string
  rental_days: number
  subtotal: string
  discount_percent: string
  discount_amount: string
  estimated_total: string
  status: string
  status_display: string
  special_request: string
  rejection_reason: string
  return_unit_status: string
  payments: PaymentRecord[]
  invoice: InvoiceRecord | null
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
const paymentNotice = ref('')
const lightboxImage = ref('')

// Assignment history for customer
const assignmentHistory = ref<AssignmentEntry[]>([])
const loadingHistory = ref(false)
const showAllHistory = ref(false)

async function loadAssignmentHistory() {
  if (!booking.value) return
  loadingHistory.value = true
  try {
    const response = await api.get(`/bookings/${booking.value.hash_id}/assignment-history/`)
    assignmentHistory.value = response.data as AssignmentEntry[]
  } catch { assignmentHistory.value = [] }
  finally { loadingHistory.value = false }
}

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
    await api.post(`/bookings/${booking.value.hash_id}/cancel/`, {
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
    case 'waiting_for_pickup': return 3
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
  const hour = parseInt(h || '0', 10)
  const ampm = hour >= 12 ? 'PM' : 'AM'
  const display = hour > 12 ? hour - 12 : hour === 0 ? 12 : hour
  return `${display}:${m} ${ampm}`
}

function docTypeLabel(type: string): string {
  return type.replace(/_/g, ' ')
}

async function initiatePayment() {
  if (!booking.value) return
  paying.value = true
  paymentNotice.value = ''
  try {
    const response = await api.post('/payments/create-session/', { booking_hash_id: booking.value.hash_id })
    if (response.data.checkout_url) window.location.href = response.data.checkout_url
    else paymentNotice.value = response.data.detail || 'Payment setup is not configured yet. Please contact support.'
  } catch (error: any) {
    paymentNotice.value = error?.response?.data?.detail || 'Unable to start payment right now. Please try again later.'
  }
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
    await loadAssignmentHistory()

    // If the customer just returned from the hosted checkout page, force a
    // gateway re-check so a missed webhook doesn't leave the booking stuck
    // in awaiting_payment.  Only do this once, when the payment query param
    // is present.
    if (route.query.payment === 'success' && booking.value?.status === 'awaiting_payment') {
      await checkPaymentStatus()
    }
  } catch { error.value = 'Booking not found.' }
  finally { loading.value = false }
}

async function checkPaymentStatus() {
  if (!booking.value) return
  try {
    const response = await api.post(`/bookings/${booking.value.hash_id}/check-payment/`)
    booking.value = response.data
  } catch { /* keep current state on failure */ }
}

const currentIdx = computed(() => booking.value ? currentStepIndex(booking.value.status) : 0)
const canCancel = computed(() => {
  if (!booking.value) return false
  return ['pending_approval', 'approved', 'awaiting_payment'].includes(booking.value.status)
})
const canPay = computed(() => ['approved', 'awaiting_payment'].includes(booking.value?.status || ''))
const stepHint = computed(() => {
  if (!booking.value) return ''
  switch (booking.value.status) {
    case 'pending_approval': return 'Waiting for admin review'
    case 'approved': return 'Booking approved — proceed to payment'
    case 'awaiting_payment': return 'Payment required to confirm booking'
    case 'confirmed': return 'Your booking is confirmed — prepare for pickup'
    case 'waiting_for_pickup': return 'Your vehicle unit is assigned — ready for pickup'
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
            <!-- Customer Profile (snapshot at booking) -->
            <div class="rounded-md border border-zinc-200 bg-white p-5">
              <h2 class="text-sm font-semibold text-zinc-900 mb-1">Your Profile</h2>
              <p class="text-xs text-zinc-400 mb-4">Details captured and submitted to the administrator when this booking was placed.</p>
              <div class="grid grid-cols-1 sm:grid-cols-3 gap-3 text-sm">
                <div>
                  <p class="text-xs text-zinc-400">Name</p>
                  <p class="text-zinc-900 font-medium truncate">{{ booking.identity_snapshot?.customer_name || booking.customer_name || '—' }}</p>
                </div>
                <div>
                  <p class="text-xs text-zinc-400">Email</p>
                  <p class="text-zinc-900 truncate">{{ booking.identity_snapshot?.customer_email || booking.customer_email || '—' }}</p>
                </div>
                <div>
                  <p class="text-xs text-zinc-400">Phone</p>
                  <p class="text-zinc-900">{{ booking.identity_snapshot?.customer_phone || booking.customer_phone || '—' }}</p>
                </div>
              </div>

              <!-- Identity Documents (immutable snapshot captured at booking) -->
              <div v-if="booking.identity_snapshot && booking.identity_snapshot.documents && booking.identity_snapshot.documents.length > 0" class="pt-4 mt-4 border-t border-zinc-100">
                <p class="text-xs font-medium text-zinc-500 uppercase tracking-wider mb-3">Identity Documents</p>
                <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div v-for="doc in booking.identity_snapshot.documents" :key="doc.id" class="p-3 rounded-md bg-zinc-50 border border-zinc-100">
                    <p class="text-xs font-medium text-zinc-700 capitalize">{{ docTypeLabel(doc.document_type) }}</p>
                    <p class="text-xs text-zinc-500 mb-2">{{ doc.document_number }}</p>
                    <div class="grid grid-cols-2 gap-2">
                      <div>
                        <p class="text-[10px] text-zinc-400 mb-1">Front</p>
                        <img v-if="doc.front_image" :src="doc.front_image" class="w-full h-16 object-cover rounded cursor-pointer hover:opacity-80 transition" @click="lightboxImage = doc.front_image" alt="Front" />
                        <div v-else class="w-full h-16 bg-zinc-200 rounded flex items-center justify-center"><span class="text-[10px] text-zinc-400">No image</span></div>
                      </div>
                      <div>
                        <p class="text-[10px] text-zinc-400 mb-1">Back</p>
                        <img v-if="doc.back_image" :src="doc.back_image" class="w-full h-16 object-cover rounded cursor-pointer hover:opacity-80 transition" @click="lightboxImage = doc.back_image" alt="Back" />
                        <div v-else class="w-full h-16 bg-zinc-200 rounded flex items-center justify-center"><span class="text-[10px] text-zinc-400">No image</span></div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
              <div v-else class="text-xs text-zinc-400 pt-4 mt-4 border-t border-zinc-100">No identity documents submitted.</div>
            </div>

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
                    'bg-cyan-100 text-cyan-800': booking.status === 'waiting_for_pickup',
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
              <!-- Assigned Unit -->
              <div v-if="booking.vehicle_unit_plate" class="p-3 rounded-md bg-zinc-50 border border-zinc-100 mt-3 mb-3">
                <p class="text-xs text-zinc-400 mb-1">Assigned Vehicle</p>
                <p class="text-sm font-mono font-semibold text-zinc-900">{{ booking.vehicle_unit_plate }}</p>
                <p v-if="booking.assigned_by" class="text-xs text-zinc-500 mt-1">Assigned by: {{ booking.assigned_by }}</p>
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
                <div class="flex justify-between text-sm"><span class="text-zinc-500">Daily Rate</span><span class="text-zinc-900">₱{{ (Number(booking.subtotal) / booking.rental_days).toLocaleString('en-PH') }}</span></div>
                <div class="flex justify-between text-sm"><span class="text-zinc-500">Rental Days</span><span class="text-zinc-900">{{ booking.rental_days }} day{{ booking.rental_days > 1 ? 's' : '' }}</span></div>
                <div class="flex justify-between text-sm"><span class="text-zinc-500">Subtotal</span><span class="text-zinc-900">₱{{ Number(booking.subtotal).toLocaleString('en-PH') }}</span></div>
                <div v-if="Number(booking.discount_amount) > 0" class="flex justify-between text-sm text-green-700"><span>Discount ({{ Number(booking.discount_percent) }}%)</span><span>− ₱{{ Number(booking.discount_amount).toLocaleString('en-PH') }}</span></div>
                <hr class="border-zinc-200" />
                <div class="flex justify-between text-sm font-semibold"><span class="text-zinc-900">Estimated Total</span><span class="text-zinc-900">₱{{ Number(booking.estimated_total).toLocaleString('en-PH') }}</span></div>
              </div>
            </div>
          </div>
          <!-- RIGHT COLUMN -->
          <div class="space-y-6">
            <!-- Payment Details -->
            <div class="rounded-md border border-zinc-200 bg-white p-6">
              <h2 class="text-sm font-semibold text-zinc-900 mb-4">Payment Details</h2>

              <!-- Status indicator -->
              <div class="rounded-md bg-zinc-50 border border-zinc-100 p-4 text-center mb-4">
                <CreditCard class="h-8 w-8 text-zinc-300 mx-auto mb-2" />
                <p class="text-xs text-zinc-500">
                  <template v-if="booking.status === 'awaiting_payment'">Payment is required to confirm your booking.</template>
                  <template v-else-if="['confirmed', 'waiting_for_pickup', 'active', 'completed'].includes(booking.status)">Payment confirmed</template>
                  <template v-else-if="booking.status === 'pending_approval'">Awaiting approval before payment</template>
                  <template v-else>No payment information available</template>
                </p>
              </div>

              <!-- Payment records -->
              <div v-if="booking.invoice || (booking.payments && booking.payments.length > 0)" class="rounded-md border border-zinc-200 overflow-hidden">
                <!-- Receipt header -->
                <div class="bg-zinc-50 border-b border-zinc-200 px-4 py-3">
                  <div class="flex items-center justify-between">
                    <p class="text-xs font-semibold text-zinc-900 uppercase tracking-wider">Receipt</p>
                    <span v-if="booking.invoice" class="text-xs font-medium" :class="{
                      'text-green-700': booking.invoice.invoice_status === 'paid',
                      'text-amber-600': booking.invoice.invoice_status === 'pending',
                      'text-zinc-500': !['paid', 'pending'].includes(booking.invoice.invoice_status),
                    }">{{ booking.invoice.invoice_status }}</span>
                  </div>
                  <p v-if="booking.invoice" class="text-[11px] text-zinc-500 mt-0.5 font-mono">{{ booking.invoice.invoice_number }}</p>
                </div>

                <!-- Receipt body -->
                <div class="px-4 py-3 space-y-2">
                  <div class="flex justify-between text-xs">
                    <span class="text-zinc-500">Booking</span>
                    <span class="text-zinc-900 font-mono">{{ booking.booking_number }}</span>
                  </div>
                  <div class="flex justify-between text-xs">
                    <span class="text-zinc-500">Vehicle</span>
                    <span class="text-zinc-900 text-right">{{ booking.vehicle_name }}</span>
                  </div>
                  <div v-if="booking.invoice?.due_date" class="flex justify-between text-xs">
                    <span class="text-zinc-500">Due Date</span>
                    <span class="text-zinc-900">{{ formatDate(booking.invoice.due_date) }}</span>
                  </div>

                  <hr class="border-dashed border-zinc-200" />

                  <div class="flex justify-between text-xs">
                    <span class="text-zinc-500">Subtotal</span>
                    <span class="text-zinc-900">₱{{ Number(booking.invoice?.subtotal ?? booking.subtotal).toLocaleString('en-PH') }}</span>
                  </div>
                  <div v-if="Number(booking.invoice?.discount ?? booking.discount_amount) > 0" class="flex justify-between text-xs text-green-700">
                    <span>Discount</span>
                    <span>− ₱{{ Number(booking.invoice?.discount ?? booking.discount_amount).toLocaleString('en-PH') }}</span>
                  </div>

                  <hr class="border-dashed border-zinc-200" />

                  <div class="flex justify-between text-sm font-semibold">
                    <span class="text-zinc-900">Total Amount</span>
                    <span class="text-zinc-900">₱{{ Number(booking.invoice?.total ?? booking.estimated_total).toLocaleString('en-PH') }}</span>
                  </div>

                  <!-- Per-payment entries -->
                  <template v-if="booking.payments && booking.payments.length > 0">
                    <hr class="border-dashed border-zinc-200" />
                    <div v-for="p in booking.payments" :key="p.id" class="space-y-1">
                      <div class="flex justify-between text-xs">
                        <span class="text-zinc-500 font-mono">{{ p.payment_number }}</span>
                        <span class="text-zinc-900 font-medium">₱{{ Number(p.amount).toLocaleString('en-PH') }}</span>
                      </div>
                      <div class="flex justify-between text-xs">
                        <span class="text-zinc-400">{{ p.payment_method || '—' }}</span>
                        <span class="text-xs font-medium" :class="{
                          'text-green-700': p.payment_status === 'paid',
                          'text-amber-600': p.payment_status === 'pending',
                          'text-red-600': ['failed', 'expired', 'cancelled'].includes(p.payment_status),
                          'text-zinc-500': !['paid', 'pending', 'failed', 'expired', 'cancelled'].includes(p.payment_status),
                        }">{{ p.payment_status }}</span>
                      </div>
                      <p v-if="p.paid_at" class="text-[11px] text-zinc-400 text-right">Paid {{ formatDateTime(p.paid_at) }}</p>
                    </div>
                  </template>
                </div>
              </div>

              <div v-if="!booking.payments?.length && !booking.invoice" class="text-xs text-zinc-400 text-center py-2">
                No payment records yet.
              </div>
            </div>

            <!-- Messages, Indicators & Reminders -->
            <div class="rounded-md border border-zinc-200 bg-white p-6 space-y-3">
              <h2 class="text-sm font-semibold text-zinc-900">Updates</h2>

              <div v-if="paymentNotice" class="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-700">
                {{ paymentNotice }}
              </div>

              <!-- Message: admin will assign unit after payment -->
              <div v-if="booking.status === 'confirmed'" class="rounded-md bg-blue-50 border border-blue-200 px-3 py-2">
                <p class="text-xs text-blue-700">
                  <span class="font-medium">Payment confirmed!</span> An administrator will assign a specific vehicle unit to your booking before your pickup date. You'll be notified once a unit is assigned.
                </p>
              </div>

              <!-- Assigned unit info (shown when assigned) -->
              <div v-if="booking.vehicle_unit_plate" class="rounded-md bg-emerald-50 border border-emerald-200 px-3 py-2">
                <p class="text-xs text-emerald-700">
                  <span class="font-medium">Vehicle assigned:</span> {{ booking.vehicle_unit_plate }}
                </p>
              </div>

              <div v-if="booking.status === 'completed'" class="text-center">
                <CheckCircle class="h-8 w-8 text-green-500 mx-auto mb-2" />
                <p class="text-xs text-green-700 font-medium">Rental Complete</p>
              </div>

              <!-- Unit history for customer -->
              <div v-if="assignmentHistory.length > 0" class="pt-2 border-t border-zinc-100">
                <p class="text-xs font-medium text-zinc-500 uppercase tracking-wider mb-2 flex items-center gap-1">
                  <RefreshCw class="h-3.5 w-3.5" /> Unit Assignment History
                </p>
                <div class="space-y-2" :class="{ 'max-h-40 overflow-y-auto': !showAllHistory && assignmentHistory.length > 5 }">
                  <div v-for="entry in (showAllHistory ? assignmentHistory : assignmentHistory.slice(0, 5))" :key="entry.id" class="text-xs p-2 rounded bg-zinc-50 border border-zinc-100">
                    <p class="text-zinc-700">
                      <span v-if="entry.previous_plate" class="text-zinc-400 line-through">{{ entry.previous_plate }}</span>
                      <span v-if="entry.previous_plate" class="text-zinc-400 mx-1">→</span>
                      <span class="font-mono font-medium text-zinc-900">{{ entry.new_plate }}</span>
                    </p>
                    <p class="text-zinc-400 mt-0.5">{{ entry.reason }}</p>
                    <p class="text-zinc-400">{{ entry.changed_by_name }} · {{ formatDateTime(entry.created_at) }}</p>
                  </div>
                  <button
                    v-if="assignmentHistory.length > 5"
                    class="text-xs text-blue-600 hover:text-blue-800 mt-2 w-full text-center"
                    @click="showAllHistory = !showAllHistory"
                  >
                    {{ showAllHistory ? 'Show less' : `Show all (${assignmentHistory.length} entries)` }}
                  </button>
                </div>
              </div>
            </div>

            <!-- Actions -->
            <div class="rounded-md border border-zinc-200 bg-white p-6 space-y-3">
              <h2 class="text-sm font-semibold text-zinc-900">Actions</h2>
              <Button v-if="canPay" class="w-full" :disabled="paying" @click="initiatePayment">{{ paying ? 'Redirecting...' : 'Pay Now' }}</Button>
              <Button v-if="canCancel" variant="ghost" class="w-full text-red-600 hover:bg-red-50" :disabled="cancelling" @click="openCancelModal">{{ cancelling ? 'Cancelling...' : 'Cancel Request' }}</Button>
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

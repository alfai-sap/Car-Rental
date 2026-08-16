<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, RouterLink } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import Navbar from '@/components/Navbar.vue'
import Button from '@/components/ui/Button.vue'
import api from '@/services/api'
import {
  ChevronLeft, Check, Clock, XCircle, AlertCircle,
  CreditCard, Car, CheckCircle, Calendar, Shield, User, Truck, RefreshCw,
} from 'lucide-vue-next'

const route = useRoute()
const auth = useAuthStore()

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

interface UnitOption {
  id: number
  plate_number: string
  status: string
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

interface AssignmentEntry {
  id: number
  previous_plate: string | null
  new_plate: string
  reason: string
  changed_by_name: string
  created_at: string
}

const booking = ref<Booking | null>(null)
const loading = ref(true)
const error = ref('')
const processing = ref(false)
const rejectReasonType = ref('')
const rejectReasonCustom = ref('')
const showRejectDialog = ref(false)
const showRejectConfirmModal = ref(false)
const lightboxImage = ref('')

// Unit assignment state
const availableUnits = ref<UnitOption[]>([])
const loadingUnits = ref(false)
const selectedUnitId = ref<number | null>(null)
const assignmentReason = ref('')
const assigningUnit = ref(false)
const showUnitForm = ref(false)

// Assignment history
const assignmentHistory = ref<AssignmentEntry[]>([])
const loadingHistory = ref(false)
const showAllHistory = ref(false)

// Return modal
const showReturnDialog = ref(false)
const returnUnitStatus = ref('available')
const completingTransaction = ref(false)

// Confirmation modals for critical operations
const showConfirmPaymentModal = ref(false)
const showMarkActiveModal = ref(false)
const showCompleteModal = ref(false)

const REJECT_REASONS = [
  { value: '', label: 'Select a reason...' },
  { value: 'vehicle_unavailable', label: 'Vehicle unavailable for selected dates' },
  { value: 'invalid_documents', label: 'Driver documents invalid or expired' },
  { value: 'incomplete_info', label: 'Customer information incomplete' },
  { value: 'policy_violation', label: 'Against business policy' },
  { value: 'unreachable', label: 'Unable to contact customer' },
  { value: 'other', label: 'Other — specify below' },
]

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

async function approveBooking() {
  if (!booking.value) return
  processing.value = true
  try {
    await api.post(`/bookings/${booking.value.hash_id}/approve/`)
    await fetchBooking()
  } finally { processing.value = false }
}

const rejectReasonText = computed(() => {
  if (rejectReasonType.value === 'other') return rejectReasonCustom.value
  const found = REJECT_REASONS.find(r => r.value === rejectReasonType.value)
  return found && found.value ? found.label : ''
})

const canConfirmReject = computed(() => {
  if (!rejectReasonType.value) return false
  if (rejectReasonType.value === 'other') return rejectReasonCustom.value.trim().length > 0
  return true
})

function openRejectModal() {
  rejectReasonType.value = ''
  rejectReasonCustom.value = ''
  showRejectDialog.value = true
  showRejectConfirmModal.value = false
}

function closeRejectModal() {
  showRejectDialog.value = false
  showRejectConfirmModal.value = false
}

function confirmRejectClick() {
  if (!canConfirmReject.value) return
  showRejectConfirmModal.value = true
}

async function rejectBooking() {
  if (!booking.value || !canConfirmReject.value) return
  processing.value = true
  try {
    await api.post(`/bookings/${booking.value.hash_id}/reject/`, { rejection_reason: rejectReasonText.value })
    showRejectDialog.value = false
    showRejectConfirmModal.value = false
    rejectReasonType.value = ''
    rejectReasonCustom.value = ''
    await fetchBooking()
  } finally { processing.value = false }
}

async function confirmPayment() {
  if (!booking.value) return
  processing.value = true
  try {
    await api.post(`/bookings/${booking.value.hash_id}/confirm/`)
    showConfirmPaymentModal.value = false
    await fetchBooking()
  } finally { processing.value = false }
}

async function markActive() {
  if (!booking.value) return
  processing.value = true
  try {
    await api.post(`/bookings/${booking.value.hash_id}/mark-active/`)
    showMarkActiveModal.value = false
    await fetchBooking()
  } finally { processing.value = false }
}

async function completeTransaction() {
  if (!booking.value) return
  const status = returnUnitStatus.value || 'available'
  if (!['available', 'maintenance', 'inactive'].includes(status)) return
  completingTransaction.value = true
  try {
    await api.post(`/bookings/${booking.value.hash_id}/mark-complete/`, { return_unit_status: status })
    await fetchBooking()
    showReturnDialog.value = false
  } finally { completingTransaction.value = false }
}

// ── Unit Assignment ──

async function loadAvailableUnits() {
  if (!booking.value) return
  loadingUnits.value = true
  showUnitForm.value = true
  try {
    const response = await api.get(`/vehicles/${booking.value.vehicle_hash_id}/units/`)
    // DRF pagination wraps results in { count, results, ... }
    const data = Array.isArray(response.data) ? response.data : (response.data.results || [])
    availableUnits.value = (data as UnitOption[]).filter(u => u.status === 'available')
  } catch { availableUnits.value = [] }
  finally { loadingUnits.value = false }
}

async function assignUnit() {
  if (!booking.value || !selectedUnitId.value) return
  assigningUnit.value = true
  try {
    await api.post(`/bookings/${booking.value.hash_id}/assign-unit/`, {
      unit_id: selectedUnitId.value,
      reason: assignmentReason.value || 'Admin assignment',
    })
    selectedUnitId.value = null
    assignmentReason.value = ''
    showUnitForm.value = false
    availableUnits.value = []
    await fetchBooking()
  } finally { assigningUnit.value = false }
}

async function loadAssignmentHistory() {
  if (!booking.value) return
  loadingHistory.value = true
  try {
    const response = await api.get(`/bookings/${booking.value.hash_id}/assignment-history/`)
    assignmentHistory.value = response.data as AssignmentEntry[]
  } catch { assignmentHistory.value = [] }
  finally { loadingHistory.value = false }
}

function openReturnDialog() {
  returnUnitStatus.value = booking.value?.return_unit_status || 'available'
  showReturnDialog.value = true
}

async function fetchBooking() {
  try {
    const response = await api.get(`/bookings/${route.params.id}/`)
    if (response.data.customer !== auth.user?.id && !auth.user?.is_staff) {
      error.value = 'Not authorized.'
    } else {
      booking.value = response.data
      await loadAssignmentHistory()
    }
  } catch {
    error.value = 'Booking not found.'
  } finally {
    loading.value = false
  }
}

async function checkPaymentStatus() {
  if (!booking.value) return
  processing.value = true
  try {
    const response = await api.post(`/bookings/${booking.value.hash_id}/check-payment/`)
    booking.value = response.data
  } catch { /* keep current state on failure */ }
  finally { processing.value = false }
}

const currentIdx = computed(() => booking.value ? currentStepIndex(booking.value.status) : 0)
const stepHint = computed(() => {
  if (!booking.value) return ''
  switch (booking.value.status) {
    case 'pending_approval': return 'Awaiting your review'
    case 'approved': return 'Customer needs to pay'
    case 'awaiting_payment': return 'Awaiting payment confirmation'
    case 'confirmed': return 'Ready for pickup'
    case 'waiting_for_pickup': return 'Unit assigned — ready for pickup'
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

        <!-- Two-column layout -->
        <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
          <!-- Left: Booking Details -->
          <div class="lg:col-span-2 space-y-6">
            <!-- Customer: Current Profile vs Snapshot (side by side) -->
            <div class="rounded-md border border-zinc-200 bg-white p-6">
              <h2 class="text-sm font-semibold text-zinc-900 mb-4">Customer</h2>

              <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <!-- Current Profile (live) -->
                <div class="rounded-md border border-zinc-100 bg-zinc-50 p-4">
                  <p class="text-xs font-medium text-zinc-500 uppercase tracking-wider mb-3">Current Profile</p>
                  <div class="flex items-start gap-2 mb-3">
                    <div class="h-8 w-8 rounded-full bg-zinc-200 flex items-center justify-center flex-shrink-0">
                      <User class="h-4 w-4 text-zinc-500" />
                    </div>
                    <div class="min-w-0">
                      <p class="text-sm font-medium text-zinc-900 truncate">{{ booking.customer_name }}</p>
                      <p class="text-xs text-zinc-500 truncate">{{ booking.customer_email }}</p>
                      <p class="text-xs text-zinc-400">{{ booking.customer_phone || 'No phone' }}</p>
                    </div>
                  </div>

                  <div v-if="booking.customer_identity_docs && booking.customer_identity_docs.length > 0" class="space-y-2">
                    <div v-for="doc in booking.customer_identity_docs" :key="doc.id" class="rounded bg-white border border-zinc-100 p-2">
                      <p class="text-[11px] font-medium text-zinc-700 capitalize">{{ doc.document_type.replace(/_/g, ' ') }}</p>
                      <p class="text-[11px] text-zinc-500">{{ doc.document_number }}</p>
                      <div class="grid grid-cols-2 gap-1.5 mt-1.5">
                        <div>
                          <p class="text-[9px] text-zinc-400 mb-0.5">Front</p>
                          <img v-if="doc.front_image" :src="doc.front_image" class="w-full h-14 object-cover rounded cursor-pointer hover:opacity-80 transition" @click="lightboxImage = doc.front_image" alt="Front" />
                          <div v-else class="w-full h-14 bg-zinc-200 rounded flex items-center justify-center"><span class="text-[9px] text-zinc-400">No image</span></div>
                        </div>
                        <div>
                          <p class="text-[9px] text-zinc-400 mb-0.5">Back</p>
                          <img v-if="doc.back_image" :src="doc.back_image" class="w-full h-14 object-cover rounded cursor-pointer hover:opacity-80 transition" @click="lightboxImage = doc.back_image" alt="Back" />
                          <div v-else class="w-full h-14 bg-zinc-200 rounded flex items-center justify-center"><span class="text-[9px] text-zinc-400">No image</span></div>
                        </div>
                      </div>
                    </div>
                  </div>
                  <div v-else class="text-xs text-zinc-400">No identity documents submitted.</div>
                </div>

                <!-- Identity Snapshot (immutable, captured at booking) -->
                <div class="rounded-md border border-amber-200 bg-amber-50 p-4">
                  <p class="text-xs font-medium text-amber-700 uppercase tracking-wider mb-3 flex items-center gap-1">
                    <Shield class="h-3.5 w-3.5" /> Snapshot (at booking)
                  </p>

                  <div v-if="booking.identity_snapshot" class="space-y-1 text-xs">
                    <p class="text-zinc-700"><span class="text-zinc-400">Name:</span> {{ booking.identity_snapshot.customer_name || '—' }}</p>
                    <p class="text-zinc-700 truncate"><span class="text-zinc-400">Email:</span> {{ booking.identity_snapshot.customer_email || '—' }}</p>
                    <p class="text-zinc-700"><span class="text-zinc-400">Phone:</span> {{ booking.identity_snapshot.customer_phone || '—' }}</p>
                    <p v-if="booking.identity_snapshot.captured_at" class="text-zinc-400">{{ formatDateTime(booking.identity_snapshot.captured_at) }}</p>
                  </div>

                  <div v-if="booking.identity_snapshot && booking.identity_snapshot.documents && booking.identity_snapshot.documents.length > 0" class="mt-3 space-y-2">
                    <div v-for="doc in booking.identity_snapshot.documents" :key="doc.id" class="rounded bg-white border border-amber-100 p-2">
                      <p class="text-[11px] font-medium text-zinc-700 capitalize">{{ doc.document_type.replace(/_/g, ' ') }}</p>
                      <p class="text-[11px] text-zinc-500">{{ doc.document_number }}</p>
                      <div class="grid grid-cols-2 gap-1.5 mt-1.5">
                        <div>
                          <p class="text-[9px] text-zinc-400 mb-0.5">Front</p>
                          <img v-if="doc.front_image" :src="doc.front_image" class="w-full h-14 object-cover rounded cursor-pointer hover:opacity-80 transition" @click="lightboxImage = doc.front_image" alt="Front" />
                          <div v-else class="w-full h-14 bg-zinc-200 rounded flex items-center justify-center"><span class="text-[9px] text-zinc-400">No image</span></div>
                        </div>
                        <div>
                          <p class="text-[9px] text-zinc-400 mb-0.5">Back</p>
                          <img v-if="doc.back_image" :src="doc.back_image" class="w-full h-14 object-cover rounded cursor-pointer hover:opacity-80 transition" @click="lightboxImage = doc.back_image" alt="Back" />
                          <div v-else class="w-full h-14 bg-zinc-200 rounded flex items-center justify-center"><span class="text-[9px] text-zinc-400">No image</span></div>
                        </div>
                      </div>
                    </div>
                  </div>
                  <div v-else class="text-xs text-zinc-400">No snapshot captured.</div>
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
                      'bg-cyan-100 text-cyan-800': booking.status === 'waiting_for_pickup',
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
                  <p class="text-sm text-zinc-900">{{ formatDateTime(booking.created_at) }}</p>
                </div>
                <div>
                  <p class="text-xs text-zinc-400">Last Updated</p>
                  <p class="text-sm text-zinc-900">{{ formatDateTime(booking.updated_at) }}</p>
                </div>
              </div>

              <!-- Vehicle info -->
              <div class="p-4 rounded-md bg-zinc-50 border border-zinc-100 mb-6">
                <p class="text-xs font-medium text-zinc-500 uppercase tracking-wider mb-3">Vehicle</p>
                <div class="grid grid-cols-2 sm:grid-cols-3 gap-2 mb-3">
                  <img v-for="img in (booking.vehicle_images || [])" :key="img.id" :src="img.image" :alt="booking.vehicle_name" class="w-full h-20 object-cover rounded cursor-pointer hover:opacity-80 transition" @click="lightboxImage = img.image" />
                </div>
                <p class="text-sm font-medium text-zinc-900">{{ booking.vehicle_name }}</p>
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
                  <span class="text-zinc-500">Daily Rate</span>
                  <span class="text-zinc-900">₱{{ (Number(booking.subtotal) / booking.rental_days).toLocaleString('en-PH') }}</span>
                </div>
                <div class="flex justify-between text-sm">
                  <span class="text-zinc-500">Rental Days</span>
                  <span class="text-zinc-900">{{ booking.rental_days }} day{{ booking.rental_days > 1 ? 's' : '' }}</span>
                </div>
                <div class="flex justify-between text-sm">
                  <span class="text-zinc-500">Subtotal</span>
                  <span class="text-zinc-900">₱{{ Number(booking.subtotal).toLocaleString('en-PH') }}</span>
                </div>
                <div v-if="Number(booking.discount_amount) > 0" class="flex justify-between text-sm text-green-700">
                  <span>Discount ({{ Number(booking.discount_percent) }}%)</span>
                  <span>− ₱{{ Number(booking.discount_amount).toLocaleString('en-PH') }}</span>
                </div>
                <hr class="border-zinc-200" />
                <div class="flex justify-between text-sm font-semibold">
                  <span class="text-zinc-900">Estimated Total</span>
                  <span class="text-zinc-900">₱{{ Number(booking.estimated_total).toLocaleString('en-PH') }}</span>
                </div>
              </div>
            </div>
          </div>

          <!-- Right: Payment Details + Admin Actions -->
          <div class="space-y-6">
            <!-- Payment Details -->
            <div class="rounded-md border border-zinc-200 bg-white p-6 space-y-3">
              <h2 class="text-sm font-semibold text-zinc-900">Payment Details</h2>

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
                    <span class="text-zinc-500">Customer</span>
                    <span class="text-zinc-900 text-right">{{ booking.customer_name }}</span>
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

            <!-- Actions -->
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
                  @click="openRejectModal"
                >
                  Reject Booking
                </Button>
              </template>

              <!-- Awaiting Payment: Confirm Payment (dev/superuser only) -->
              <template v-else-if="booking.status === 'awaiting_payment' && auth.user?.allow_manual_payment_confirm">
                <Button
                  class="w-full"
                  :disabled="processing"
                  @click="showConfirmPaymentModal = true"
                >
                  {{ processing ? '...' : 'Confirm Payment' }}
                </Button>
              </template>

              <!-- Awaiting Payment: waiting on gateway confirmation -->
              <template v-else-if="booking.status === 'awaiting_payment'">
                <p class="text-xs text-zinc-400 text-center">
                  Awaiting payment confirmation from the gateway.
                </p>
                <Button variant="ghost" size="sm" class="w-full text-xs" :disabled="processing" @click="checkPaymentStatus">
                  {{ processing ? 'Checking...' : 'Refresh Payment Status' }}
                </Button>
              </template>

              <!-- Confirmed / Waiting for Pickup: Assign Unit + Mark Active -->
              <template v-else-if="booking.status === 'confirmed' || booking.status === 'waiting_for_pickup'">
                <!-- Unit Assignment -->
                <div class="p-3 rounded-md bg-zinc-50 border border-zinc-100 space-y-2">
                  <p class="text-xs font-medium text-zinc-500 uppercase tracking-wider flex items-center gap-1">
                    <Truck class="h-3.5 w-3.5" /> Assigned Unit
                  </p>
                  <p v-if="booking.vehicle_unit_plate" class="text-sm font-mono font-semibold text-zinc-900">
                    {{ booking.vehicle_unit_plate }}
                    <span class="text-xs text-zinc-400 font-normal ml-1">({{ booking.vehicle_unit_status }})</span>
                  </p>
                  <p v-else class="text-xs text-zinc-400">No unit assigned</p>

                  <Button variant="ghost" size="sm" class="w-full text-xs" @click="loadAvailableUnits">
                    {{ loadingUnits ? 'Loading...' : (booking.vehicle_unit_plate ? 'Change Unit' : 'Assign Unit') }}
                  </Button>

                  <!-- Unit selector (shown after clicking Assign/Change) -->
                  <div v-if="showUnitForm && !loadingUnits && availableUnits.length > 0" class="space-y-2 pt-2 border-t border-zinc-200">
                    <select v-model="selectedUnitId" class="w-full rounded border border-zinc-300 text-xs p-2">
                      <option :value="null" disabled>Select a unit...</option>
                      <option v-for="u in availableUnits" :key="u.id" :value="u.id">{{ u.plate_number }}</option>
                    </select>
                    <input v-model="assignmentReason" type="text" placeholder="Reason (optional)" class="w-full rounded border border-zinc-300 text-xs p-2" />
                    <div class="flex gap-2">
                      <Button variant="ghost" size="sm" class="flex-1 text-xs" @click="showUnitForm = false">Cancel</Button>
                      <Button size="sm" class="flex-1" :disabled="!selectedUnitId || assigningUnit" @click="assignUnit">
                        {{ assigningUnit ? 'Assigning...' : 'Assign' }}
                      </Button>
                    </div>
                  </div>
                  <p v-else-if="showUnitForm && !loadingUnits && availableUnits.length === 0" class="text-xs text-amber-600">
                    No available units for this vehicle.
                    <button class="underline ml-1" @click="showUnitForm = false">Close</button>
                  </p>
                </div>

                <!-- Mark Active -->
                <Button
                  class="w-full"
                  :disabled="processing || !booking.vehicle_unit"
                  @click="showMarkActiveModal = true"
                >
                  {{ processing ? '...' : 'Mark as Active (Pickup)' }}
                </Button>
                <p v-if="!booking.vehicle_unit" class="text-xs text-zinc-400 text-center">Assign a vehicle unit before activating</p>
              </template>

              <!-- Persisted unit info for active/completed (read-only) -->
              <div v-if="booking.vehicle_unit_plate && (booking.status === 'active' || booking.status === 'completed')" class="p-3 rounded-md bg-zinc-50 border border-zinc-100 space-y-1">
                <p class="text-xs font-medium text-zinc-500 uppercase tracking-wider flex items-center gap-1">
                  <Truck class="h-3.5 w-3.5" /> Assigned Unit
                </p>
                <p class="text-sm font-mono font-semibold text-zinc-900">
                  {{ booking.vehicle_unit_plate }}
                  <span class="text-xs text-zinc-400 font-normal ml-1">({{ booking.vehicle_unit_status }})</span>
                </p>
              </div>

              <!-- Active: Complete (with return status) -->
              <template v-if="booking.status === 'active'">
                <Button
                  class="w-full"
                  @click="showCompleteModal = true"
                >
                  Complete Transaction
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

              <!-- Assignment History (available in all statuses) -->
              <div v-if="assignmentHistory.length > 0" class="pt-4 border-t border-zinc-100">
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
          </div>
        </div>
      </template>
    </main>

    <!-- Lightbox -->
    <Teleport to="body">
      <div v-if="lightboxImage" class="fixed inset-0 z-[100] bg-black/90 flex items-center justify-center" @click="lightboxImage = ''">
        <button @click="lightboxImage = ''" class="absolute top-4 right-4 text-white/70 hover:text-white"><XCircle class="h-6 w-6" /></button>
        <img :src="lightboxImage" class="max-w-[90vw] max-h-[85vh] object-contain" />
      </div>
    </Teleport>

    <!-- Reject Modal -->
    <Teleport to="body">
      <div v-if="showRejectDialog" class="fixed inset-0 z-[200] flex items-center justify-center p-4">
        <div class="absolute inset-0 bg-black/50" @click="closeRejectModal" />
        <div class="relative bg-white rounded-lg shadow-xl max-w-md w-full p-6 space-y-4">
          <h3 class="text-lg font-semibold text-zinc-900">Reject Booking</h3>
          <p class="text-sm text-zinc-500">Please provide a reason for rejecting this booking request.</p>

          <!-- Reason dropdown -->
          <div class="space-y-1">
            <label class="text-xs font-medium text-zinc-700">Reason</label>
            <select
              v-model="rejectReasonType"
              class="h-9 w-full rounded-md border border-zinc-300 bg-white px-3 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-zinc-400"
              :disabled="processing"
            >
              <option v-for="reason in REJECT_REASONS" :key="reason.value" :value="reason.value">{{ reason.label }}</option>
            </select>
          </div>

          <!-- Custom reason textarea -->
          <div v-if="rejectReasonType === 'other'" class="space-y-1">
            <label class="text-xs font-medium text-zinc-700">Please specify</label>
            <textarea
              v-model="rejectReasonCustom"
              rows="2"
              placeholder="Enter your reason..."
              class="w-full rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm placeholder:text-zinc-400 focus:outline-none focus:ring-2 focus:ring-zinc-400"
              :disabled="processing"
            />
          </div>

          <div class="flex gap-2 pt-2">
            <Button variant="ghost" class="flex-1" @click="closeRejectModal" :disabled="processing">Cancel</Button>
            <Button
              class="flex-1 bg-red-600 hover:bg-red-700 text-white"
              :disabled="!canConfirmReject || processing"
              @click="confirmRejectClick"
            >
              {{ processing ? '...' : 'Reject Booking' }}
            </Button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Reject Confirmation Modal -->
    <Teleport to="body">
      <div v-if="showRejectConfirmModal" class="fixed inset-0 z-[250] flex items-center justify-center p-4">
        <div class="absolute inset-0 bg-black/50" />
        <div class="relative bg-white rounded-lg shadow-xl max-w-sm w-full p-6 space-y-4 text-center">
          <XCircle class="h-10 w-10 text-red-500 mx-auto" />
          <h3 class="text-lg font-semibold text-zinc-900">Confirm Rejection</h3>
          <p class="text-sm text-zinc-500">Are you sure you want to reject this booking?</p>
          <p class="text-xs text-zinc-400 italic">"{{ rejectReasonText }}"</p>
          <div class="flex gap-2 pt-2">
            <Button variant="ghost" class="flex-1" @click="showRejectConfirmModal = false" :disabled="processing">Back</Button>
            <Button
              class="flex-1 bg-red-600 hover:bg-red-700 text-white"
              :disabled="processing"
              @click="rejectBooking"
            >
              {{ processing ? 'Rejecting...' : 'Yes, Reject' }}
            </Button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Confirm Payment Modal -->
    <Teleport to="body">
      <div v-if="showConfirmPaymentModal" class="fixed inset-0 z-[200] flex items-center justify-center p-4">
        <div class="absolute inset-0 bg-black/50" @click="showConfirmPaymentModal = false" />
        <div class="relative bg-white rounded-lg shadow-xl max-w-md w-full p-6 space-y-4">
          <div class="flex items-center gap-3">
            <div class="h-10 w-10 rounded-full bg-amber-100 flex items-center justify-center flex-shrink-0">
              <CreditCard class="h-5 w-5 text-amber-600" />
            </div>
            <div>
              <h3 class="text-lg font-semibold text-zinc-900">Confirm Payment</h3>
              <p class="text-xs text-amber-600 font-medium">Critical action — please review</p>
            </div>
          </div>

          <div class="rounded-md bg-zinc-50 border border-zinc-100 p-4 space-y-2 text-sm">
            <div class="flex justify-between">
              <span class="text-zinc-500">Customer</span>
              <span class="font-medium text-zinc-900">{{ booking?.customer_name }}</span>
            </div>
            <div class="flex justify-between">
              <span class="text-zinc-500">Vehicle</span>
              <span class="font-medium text-zinc-900">{{ booking?.vehicle_name }}</span>
            </div>
            <div class="flex justify-between">
              <span class="text-zinc-500">Total</span>
              <span class="font-semibold text-zinc-900">₱{{ Number(booking?.estimated_total || 0).toLocaleString('en-PH') }}</span>
            </div>
          </div>

          <p class="text-xs text-zinc-500">
            This will confirm the customer's payment and finalize the booking. Only proceed if the payment has been verified.
          </p>

          <div class="flex gap-2 pt-2">
            <Button variant="ghost" class="flex-1" @click="showConfirmPaymentModal = false" :disabled="processing">Cancel</Button>
            <Button class="flex-1 bg-amber-600 hover:bg-amber-700 text-white" :disabled="processing" @click="confirmPayment">
              {{ processing ? 'Confirming...' : 'Yes, Confirm Payment' }}
            </Button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Mark Active Modal -->
    <Teleport to="body">
      <div v-if="showMarkActiveModal" class="fixed inset-0 z-[200] flex items-center justify-center p-4">
        <div class="absolute inset-0 bg-black/50" @click="showMarkActiveModal = false" />
        <div class="relative bg-white rounded-lg shadow-xl max-w-md w-full p-6 space-y-4">
          <div class="flex items-center gap-3">
            <div class="h-10 w-10 rounded-full bg-blue-100 flex items-center justify-center flex-shrink-0">
              <Car class="h-5 w-5 text-blue-600" />
            </div>
            <div>
              <h3 class="text-lg font-semibold text-zinc-900">Mark as Active (Pickup)</h3>
              <p class="text-xs text-blue-600 font-medium">Critical action — please review</p>
            </div>
          </div>

          <div class="rounded-md bg-zinc-50 border border-zinc-100 p-4 space-y-2 text-sm">
            <div class="flex justify-between">
              <span class="text-zinc-500">Customer</span>
              <span class="font-medium text-zinc-900">{{ booking?.customer_name }}</span>
            </div>
            <div class="flex justify-between">
              <span class="text-zinc-500">Vehicle</span>
              <span class="font-medium text-zinc-900">{{ booking?.vehicle_name }}</span>
            </div>
            <div class="flex justify-between">
              <span class="text-zinc-500">Assigned Unit</span>
              <span class="font-semibold font-mono text-zinc-900">{{ booking?.vehicle_unit_plate || '—' }}</span>
            </div>
            <div class="flex justify-between">
              <span class="text-zinc-500">Pickup Date</span>
              <span class="font-medium text-zinc-900">{{ formatDate(booking?.pickup_date || '') }}</span>
            </div>
          </div>

          <p class="text-xs text-zinc-500">
            This confirms the vehicle has been picked up and marks the rental as active. Verify the customer's identity and the vehicle condition before proceeding.
          </p>

          <div class="flex gap-2 pt-2">
            <Button variant="ghost" class="flex-1" @click="showMarkActiveModal = false" :disabled="processing">Cancel</Button>
            <Button class="flex-1 bg-blue-600 hover:bg-blue-700 text-white" :disabled="processing" @click="markActive">
              {{ processing ? 'Activating...' : 'Yes, Mark as Active' }}
            </Button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Complete Transaction Modal -->
    <Teleport to="body">
      <div v-if="showCompleteModal" class="fixed inset-0 z-[200] flex items-center justify-center p-4">
        <div class="absolute inset-0 bg-black/50" @click="showCompleteModal = false" />
        <div class="relative bg-white rounded-lg shadow-xl max-w-md w-full p-6 space-y-4">
          <div class="flex items-center gap-3">
            <div class="h-10 w-10 rounded-full bg-emerald-100 flex items-center justify-center flex-shrink-0">
              <CheckCircle class="h-5 w-5 text-emerald-600" />
            </div>
            <div>
              <h3 class="text-lg font-semibold text-zinc-900">Complete Transaction</h3>
              <p class="text-xs text-emerald-600 font-medium">Final step — please review</p>
            </div>
          </div>

          <div class="rounded-md bg-zinc-50 border border-zinc-100 p-4 space-y-2 text-sm">
            <div class="flex justify-between">
              <span class="text-zinc-500">Customer</span>
              <span class="font-medium text-zinc-900">{{ booking?.customer_name }}</span>
            </div>
            <div class="flex justify-between">
              <span class="text-zinc-500">Vehicle</span>
              <span class="font-medium text-zinc-900">{{ booking?.vehicle_name }}</span>
            </div>
            <div class="flex justify-between">
              <span class="text-zinc-500">Unit</span>
              <span class="font-semibold font-mono text-zinc-900">{{ booking?.vehicle_unit_plate || '—' }}</span>
            </div>
          </div>

          <p class="text-xs text-zinc-500">
            This marks the transaction as complete and returns the vehicle to the fleet. Ensure the vehicle has been returned and inspected before proceeding.
          </p>

          <div class="flex gap-2 pt-2">
            <Button variant="ghost" class="flex-1" @click="showCompleteModal = false">Cancel</Button>
            <Button class="flex-1 bg-emerald-600 hover:bg-emerald-700 text-white" @click="openReturnDialog(); showCompleteModal = false">
              Continue to Return
            </Button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Return Dialog -->
    <Teleport to="body">
      <div v-if="showReturnDialog" class="fixed inset-0 z-[200] flex items-center justify-center p-4">
        <div class="absolute inset-0 bg-black/50" @click="showReturnDialog = false" />
        <div class="relative bg-white rounded-lg shadow-xl max-w-md w-full p-6 space-y-4">
          <h3 class="text-lg font-semibold text-zinc-900">Complete Transaction</h3>
          <p class="text-sm text-zinc-500">Select the post-return status of the vehicle unit.</p>

          <div class="space-y-1">
            <label class="text-xs font-medium text-zinc-700">Vehicle Status After Return</label>
            <select v-model="returnUnitStatus" class="h-9 w-full rounded-md border border-zinc-300 bg-white px-3 py-1 text-sm">
              <option value="available">Available</option>
              <option value="maintenance">Maintenance</option>
              <option value="inactive">Inactive</option>
            </select>
          </div>

          <div class="flex gap-2 pt-2">
            <Button variant="ghost" class="flex-1" @click="showReturnDialog = false">Cancel</Button>
            <Button class="flex-1" :disabled="completingTransaction" @click="completeTransaction">
              {{ completingTransaction ? 'Completing...' : 'Complete Transaction' }}
            </Button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

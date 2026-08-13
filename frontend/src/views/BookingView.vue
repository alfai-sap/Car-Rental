<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useRoute, RouterLink } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import Navbar from '@/components/Navbar.vue'
import Button from '@/components/ui/Button.vue'
import Label from '@/components/ui/Label.vue'
import { ChevronLeft, ChevronRight, AlertTriangle } from 'lucide-vue-next'
import api from '@/services/api'

interface Vehicle {
  id: number
  make: string
  model: string
  year: number
  price_per_day: string
  primary_image: string | null
}

interface IdentityDoc {
  id: number
  document_type: string
  document_number: string
  front_image: string
  back_image: string | null
}

const route = useRoute()
const auth = useAuthStore()

const vehicle = ref<Vehicle | null>(null)
const loading = ref(true)
const error = ref('')

// â”€â”€ Driver info â”€â”€
const identityDocs = ref<IdentityDoc[]>([])
const checkingDocs = ref(true)
const hasDriverLicense = computed(() =>
  identityDocs.value.some(doc => doc.document_type === 'drivers_license')
)

// â”€â”€ Calendar state â”€â”€
const calendarMonth = ref(new Date())
const startStr = ref('')  // "YYYY-MM-DD"
const endStr = ref('')    // "YYYY-MM-DD"
const pickupTime = ref('09:00')
const returnTime = ref('17:00')
const specialRequest = ref('')

// Computed date strings for API
const pickupDate = computed(() => startStr.value)
const returnDate = computed(() => endStr.value)

// Availability state
const checkingAvailability = ref(false)
const availability = ref<{
  available: boolean
  reason?: string
  total_units?: number
  available_units?: number
  rental_days?: number
  price_per_day?: string
  subtotal?: string
  estimated_total?: string
} | null>(null)

// Auto-check availability when both dates are selected
watch([startStr, endStr], async () => {
  if (!startStr.value || !endStr.value || !vehicle.value) {
    availability.value = null
    return
  }
  checkingAvailability.value = true
  try {
    const response = await api.get('/bookings/availability/', {
      params: {
        vehicle_id: vehicle.value.id,
        start_date: startStr.value,
        end_date: endStr.value,
      },
    })
    availability.value = response.data
  } catch {
    availability.value = { available: false, reason: 'Could not check availability.' }
  } finally {
    checkingAvailability.value = false
  }
})

// Submission
const submitting = ref(false)
const submitError = ref('')
const submitSuccess = ref(false)

// â”€â”€ Calendar helpers â”€â”€
function toDateString(d: Date): string {
  return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0')
}

function parseDate(s: string): Date {
  return new Date(s + 'T00:00:00')
}

const today = computed(() => {
  const d = new Date()
  d.setHours(0, 0, 0, 0)
  return d
})

const todayStr = computed(() => toDateString(today.value))

const monthLabel = computed(() => {
  return calendarMonth.value.toLocaleDateString('en-US', { month: 'long', year: 'numeric' })
})

// Generate the 6-week grid for the current calendar month
const calendarWeeks = computed(() => {
  const year = calendarMonth.value.getFullYear()
  const month = calendarMonth.value.getMonth()
  const firstDay = new Date(year, month, 1)
  const startOfGrid = new Date(firstDay)
  startOfGrid.setDate(1 - firstDay.getDay())

  const weeks: Array<Array<{ dateStr: string; isCurrentMonth: boolean; isPast: boolean; isStart: boolean; isEnd: boolean; inRange: boolean }>> = []

  for (let w = 0; w < 6; w++) {
    const week: typeof weeks[0] = []
    for (let d = 0; d < 7; d++) {
      const day = new Date(startOfGrid)
      day.setDate(startOfGrid.getDate() + w * 7 + d)
      const ds = toDateString(day)
      const isCurrentMonth = day.getMonth() === month
      const isPast = day.getTime() < today.value.getTime()
      const isStart = ds === startStr.value
      const isEnd = ds === endStr.value
      const inRange = Boolean(startStr.value && endStr.value && ds > startStr.value && ds < endStr.value)

      week.push({ dateStr: ds, isCurrentMonth, isPast, isStart, isEnd, inRange })
    }
    weeks.push(week)
  }
  return weeks
})

function prevMonth() {
  calendarMonth.value = new Date(calendarMonth.value.getFullYear(), calendarMonth.value.getMonth() - 1, 1)
}

function nextMonth() {
  calendarMonth.value = new Date(calendarMonth.value.getFullYear(), calendarMonth.value.getMonth() + 1, 1)
}

function onDayClick(ds: string, isPast: boolean, isCurrentMonth: boolean) {
  if (isPast || !isCurrentMonth) return

  // No start yet, or both already set â†’ start fresh
  if (!startStr.value || (startStr.value && endStr.value)) {
    startStr.value = ds
    endStr.value = ''
    availability.value = null
    return
  }

  // Have start, no end â†’ this click finishes the range
  if (ds < startStr.value) {
    // Clicked before start â†’ flip
    startStr.value = ds
    availability.value = null
  } else {
    endStr.value = ds
  }
}

function clearSelection() {
  startStr.value = ''
  endStr.value = ''
  availability.value = null
}

const startDate = computed(() => startStr.value ? parseDate(startStr.value) : null)
const endDate = computed(() => endStr.value ? parseDate(endStr.value) : null)

const canSubmit = computed(() => {
  return (
    auth.isAuthenticated &&
    auth.user?.is_verified &&
    hasDriverLicense.value &&
    startStr.value &&
    endStr.value &&
    availability.value?.available === true &&
    !submitting.value &&
    !submitSuccess.value
  )
})

// Local rental-day calculation (inclusive: Aug 1â€“2 = 2 days, Aug 1â€“1 = 1 day)
const rentalDays = computed(() => {
  if (!startStr.value || !endStr.value) return null
  const s = parseDate(startStr.value)
  const e = parseDate(endStr.value)
  return Math.max(1, Math.round((e.getTime() - s.getTime()) / 86400000) + 1)
})

const pricePerDay = computed(() => vehicle.value ? Number(vehicle.value.price_per_day) : 0)

const estimatedTotal = computed(() => {
  if (rentalDays.value === null) return null
  return pricePerDay.value * rentalDays.value
})

async function handleSubmit() {
  if (!canSubmit.value || !vehicle.value) return
  submitting.value = true
  submitError.value = ''
  try {
    await api.post('/bookings/', {
      vehicle: vehicle.value.id,
      pickup_date: pickupDate.value,
      return_date: returnDate.value,
      pickup_time: pickupTime.value,
      return_time: returnTime.value,
      special_request: specialRequest.value,
    })
    submitSuccess.value = true
  } catch (err: unknown) {
    const data = (err as { response?: { data?: Record<string, string[]> | { detail?: string } } })?.response?.data
    if (data) {
      if (typeof data === 'object' && 'detail' in data) {
        submitError.value = data.detail as string
      } else {
        const messages = Object.values(data as Record<string, string[]>).flat()
        submitError.value = messages.join('. ')
      }
    } else {
      submitError.value = 'Failed to submit booking.'
    }
  } finally {
    submitting.value = false
  }
}

onMounted(async () => {
  try {
    const [vehicleRes, docsRes] = await Promise.all([
      api.get(`/vehicles/${route.params.id}/`),
      api.get('/identity-documents/'),
    ])
    vehicle.value = vehicleRes.data
    identityDocs.value = docsRes.data
  } catch {
    error.value = 'Vehicle not found.'
  } finally {
    loading.value = false
    checkingDocs.value = false
  }
})

const DAYS = ['Su', 'Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa']
</script>

<template>
  <div class="min-h-screen flex flex-col bg-zinc-50">
    <Navbar />

    <main class="flex-1 max-w-3xl mx-auto px-4 pt-24 pb-16 w-full">
      <!-- Loading -->
      <div v-if="loading" class="text-center py-20">
        <p class="text-sm text-zinc-500">Loading vehicle...</p>
      </div>

      <!-- Error -->
      <div v-else-if="error" class="text-center py-20">
        <p class="text-sm text-zinc-500">{{ error }}</p>
        <RouterLink to="/vehicles" class="text-sm text-zinc-900 font-medium hover:underline mt-2 inline-block">
          Back to vehicles
        </RouterLink>
      </div>

      <!-- Success -->
      <div v-else-if="submitSuccess" class="text-center py-20">
        <div class="inline-flex items-center justify-center w-16 h-16 rounded-full bg-green-100 mb-6">
          <svg class="w-8 h-8 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
          </svg>
        </div>
        <h1 class="text-2xl font-semibold text-zinc-900 mb-2">Booking Submitted!</h1>
        <p class="text-sm text-zinc-500 mb-6">
          Your booking request has been submitted for approval.
          You'll be notified once the administrator reviews it.
        </p>
        <RouterLink to="/vehicles" class="text-sm text-zinc-900 font-medium hover:underline">
          Browse more vehicles
        </RouterLink>
      </div>

      <template v-else-if="vehicle">
        <!-- Back Link -->
        <RouterLink :to="`/vehicles/${vehicle.id}`" class="inline-flex items-center gap-1 text-sm text-zinc-500 hover:text-zinc-900 mb-6">
          <ChevronLeft class="h-4 w-4" /> Back to vehicle
        </RouterLink>

        <h1 class="text-2xl font-semibold text-zinc-900 mb-8">Book {{ vehicle.make }} {{ vehicle.model }}</h1>

        <!-- Not Logged In -->
        <div v-if="!auth.isAuthenticated" class="rounded-md border border-zinc-200 bg-surface p-6 text-center mb-8">
          <p class="text-sm text-zinc-600 mb-4">You need to be logged in to book a vehicle.</p>
          <RouterLink to="/login">
            <Button>Sign In</Button>
          </RouterLink>
        </div>

        <!-- Not Verified -->
        <div v-else-if="!auth.user?.is_verified" class="rounded-md border border-amber-200 bg-amber-50 p-6 text-center mb-8">
          <p class="text-sm text-amber-800 mb-4">Please verify your email address before booking.</p>
          <RouterLink to="/profile" class="text-sm text-amber-900 font-medium hover:underline">
            Go to Profile
          </RouterLink>
        </div>

        <!-- No Driver License -->
        <div v-else-if="!checkingDocs && !hasDriverLicense" class="rounded-md border border-amber-200 bg-amber-50 p-6 text-center mb-8">
          <AlertTriangle class="h-5 w-5 text-amber-600 mx-auto mb-2" />
          <p class="text-sm text-amber-800 mb-4">
            You need to upload your driver's license before booking a vehicle.
          </p>
          <RouterLink to="/profile" class="text-sm text-amber-900 font-medium hover:underline">
            Go to Profile
          </RouterLink>
        </div>

        <!-- Booking Form -->
        <div v-else class="grid grid-cols-1 lg:grid-cols-5 gap-8">
          <!-- Form Column -->
          <div class="lg:col-span-3 space-y-6">
            <!-- Date Range Calendar -->
            <div class="rounded-md border border-zinc-200 bg-surface p-6">
              <div class="flex items-center justify-between mb-4">
                <h2 class="text-sm font-semibold text-zinc-900">Select Rental Dates</h2>
                <button
                  v-if="startStr || endStr"
                  @click="clearSelection"
                  class="text-xs text-zinc-500 hover:text-zinc-900 underline"
                >
                  Clear
                </button>
              </div>

              <!-- Selected dates indicator -->
              <div v-if="startStr" class="flex items-center gap-2 mb-4 text-sm">
                <span class="text-zinc-900 font-medium">
                  {{ startDate?.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }) }}
                </span>
                <span v-if="endStr" class="text-zinc-400">â†’</span>
                <span v-if="endStr" class="text-zinc-900 font-medium">
                  {{ endDate?.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }) }}
                </span>
                <span v-if="!endStr" class="text-xs text-zinc-400 italic">â€” select end date</span>
              </div>

              <!-- Calendar Header -->
              <div class="flex items-center justify-between mb-3">
                <button @click="prevMonth" class="h-8 w-8 flex items-center justify-center rounded hover:bg-zinc-100 text-zinc-500">
                  <ChevronLeft class="h-4 w-4" />
                </button>
                <span class="text-sm font-medium text-zinc-900">{{ monthLabel }}</span>
                <button @click="nextMonth" class="h-8 w-8 flex items-center justify-center rounded hover:bg-zinc-100 text-zinc-500">
                  <ChevronRight class="h-4 w-4" />
                </button>
              </div>

              <!-- Day headers -->
              <div class="grid grid-cols-7 mb-1">
                <div v-for="d in DAYS" :key="d" class="text-center text-xs font-medium text-zinc-400 py-1">
                  {{ d }}
                </div>
              </div>

              <!-- Calendar grid -->
              <div class="space-y-0.5">
                <div v-for="(week, wi) in calendarWeeks" :key="wi" class="grid grid-cols-7">
                  <button
                    v-for="(day, di) in week"
                    :key="di"
                    type="button"
                    @click="onDayClick(day.dateStr, day.isPast, day.isCurrentMonth)"
                    :disabled="day.isPast || !day.isCurrentMonth"
                    class="relative h-10 text-sm transition-colors"
                    :class="[
                      !day.isCurrentMonth ? 'text-zinc-200 cursor-default' : '',
                      day.isPast ? 'text-zinc-300 cursor-default' : '',
                      !day.isPast && day.isCurrentMonth && !day.isStart && !day.isEnd && !day.inRange ? 'hover:bg-zinc-100 cursor-pointer text-zinc-700' : '',
                      day.inRange ? 'border-t border-b border-zinc-300 bg-zinc-50 text-zinc-700' : '',
                      day.isStart && day.isEnd
                        ? 'rounded-md bg-ink text-ink-foreground font-medium'
                        : '',
                      day.isStart && !day.isEnd
                        ? 'rounded-l-md bg-ink text-ink-foreground font-medium'
                        : '',
                      day.isEnd && !day.isStart
                        ? 'rounded-r-md bg-ink text-ink-foreground font-medium'
                        : '',
                    ]"
                  >
                    {{ day.isCurrentMonth ? new Date(day.dateStr + 'T00:00:00').getDate() : '' }}
                  </button>
                </div>
              </div>
            </div>

            <!-- Pickup & Return Details -->
            <div class="rounded-md border border-zinc-200 bg-surface p-6">
              <h2 class="text-sm font-semibold text-zinc-900 mb-4">Schedule</h2>
              <div class="grid grid-cols-2 gap-4">
                <!-- Pickup -->
                <div class="rounded-md border border-zinc-100 bg-zinc-50 p-4">
                  <p class="text-xs font-medium text-zinc-500 uppercase tracking-wider mb-3">Pickup</p>
                  <div class="space-y-3">
                    <div>
                      <p class="text-xs text-zinc-400">Date</p>
                      <p class="text-sm font-medium text-zinc-900">
                        {{ startDate?.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }) || 'â€”' }}
                      </p>
                    </div>
                    <div class="space-y-1">
                      <Label>Time</Label>
                      <select
                        v-model="pickupTime"
                        class="h-9 w-full rounded-md border border-zinc-300 bg-surface px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-zinc-400"
                      >
                        <option value="06:00">06:00 AM</option>
                        <option value="07:00">07:00 AM</option>
                        <option value="08:00">08:00 AM</option>
                        <option value="09:00">09:00 AM</option>
                        <option value="10:00">10:00 AM</option>
                        <option value="11:00">11:00 AM</option>
                        <option value="12:00">12:00 PM</option>
                        <option value="13:00">01:00 PM</option>
                        <option value="14:00">02:00 PM</option>
                        <option value="15:00">03:00 PM</option>
                        <option value="16:00">04:00 PM</option>
                        <option value="17:00">05:00 PM</option>
                      </select>
                    </div>
                  </div>
                </div>

                <!-- Return -->
                <div class="rounded-md border border-zinc-100 bg-zinc-50 p-4">
                  <p class="text-xs font-medium text-zinc-500 uppercase tracking-wider mb-3">Return</p>
                  <div class="space-y-3">
                    <div>
                      <p class="text-xs text-zinc-400">Date</p>
                      <p class="text-sm font-medium text-zinc-900">
                        {{ endDate?.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }) || 'â€”' }}
                      </p>
                    </div>
                    <div class="space-y-1">
                      <Label>Time</Label>
                      <select
                        v-model="returnTime"
                        class="h-9 w-full rounded-md border border-zinc-300 bg-surface px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-zinc-400"
                      >
                        <option value="06:00">06:00 AM</option>
                        <option value="07:00">07:00 AM</option>
                        <option value="08:00">08:00 AM</option>
                        <option value="09:00">09:00 AM</option>
                        <option value="10:00">10:00 AM</option>
                        <option value="11:00">11:00 AM</option>
                        <option value="12:00">12:00 PM</option>
                        <option value="13:00">01:00 PM</option>
                        <option value="14:00">02:00 PM</option>
                        <option value="15:00">03:00 PM</option>
                        <option value="16:00">04:00 PM</option>
                        <option value="17:00">05:00 PM</option>
                      </select>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- Special Requests -->
            <div class="rounded-md border border-zinc-200 bg-surface p-6">
              <h2 class="text-sm font-semibold text-zinc-900 mb-4">Additional Information</h2>
              <div class="space-y-2">
                <Label>Special Requests (Optional)</Label>
                <textarea
                  v-model="specialRequest"
                  rows="3"
                  class="flex w-full rounded-md border border-zinc-300 bg-surface px-3 py-2 text-sm placeholder:text-zinc-400 focus:outline-none focus:ring-2 focus:ring-zinc-400"
                  placeholder="Any special requirements..."
                />
              </div>
            </div>

            <!-- Submit -->
            <!-- Unified message container -->
            <div
              v-if="startStr && endStr && !submitSuccess"
              class="rounded-md p-3 text-sm"
              :class="[
                checkingAvailability ? 'bg-zinc-50 border border-zinc-200 text-zinc-500' : '',
                !checkingAvailability && availability?.available ? 'bg-green-50 border border-green-200 text-green-700' : '',
                !checkingAvailability && availability && !availability.available ? 'bg-red-50 border border-red-200 text-red-700' : '',
              ]"
            >
              <template v-if="checkingAvailability">Checking availability...</template>
              <template v-else-if="availability?.available">
                Vehicle is available for these dates.
                <span v-if="availability.total_units">({{ availability.available_units }} of {{ availability.total_units }} available)</span>
              </template>
              <template v-else-if="availability && !availability.available">{{ availability.reason || 'Vehicle is not available for these dates.' }}</template>
            </div>

            <p v-if="submitError" class="text-sm text-red-600">{{ submitError }}</p>
            <Button
              class="w-full"
              :disabled="!canSubmit || submitting"
              @click="handleSubmit"
            >
              {{ submitting ? 'Submitting...' : 'Submit Booking Request' }}
            </Button>
            <p v-if="startStr && !canSubmit && !submitSuccess" class="text-xs text-zinc-400 text-center">
              <template v-if="!hasDriverLicense && !checkingDocs">Please upload your driver's license in your profile first.</template>
              <template v-else-if="startStr && endStr && availability && !availability.available">Vehicle is not available for the selected dates.</template>
              <template v-else-if="startStr && endStr && !availability">Checking availability...</template>
              <template v-else-if="!startStr || !endStr">Please select both a start and end date to submit your booking request.</template>
            </p>
          </div>

          <!-- Sidebar Summary -->
          <div class="lg:col-span-2">
            <div class="rounded-md border border-zinc-200 bg-surface p-6 space-y-4 sticky top-24">
              <h2 class="text-sm font-semibold text-zinc-900">Booking Summary</h2>

              <div>
                <p class="text-xs text-zinc-500">Vehicle</p>
                <p class="text-sm font-medium text-zinc-900">{{ vehicle.year }} {{ vehicle.make }} {{ vehicle.model }}</p>
              </div>

              <div v-if="startDate && endDate">
                <p class="text-xs text-zinc-500">Rental Period</p>
                <p class="text-sm font-medium text-zinc-900">
                  {{ startDate.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) }}
                  â€”
                  {{ endDate.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }) }}
                </p>
              </div>

              <hr class="border-zinc-200" />

              <div>
                <p class="text-xs text-zinc-500">Daily Rate</p>
                <p class="text-sm font-medium text-zinc-900">â‚±{{ pricePerDay.toLocaleString('en-PH') }}</p>
              </div>

              <div v-if="rentalDays !== null">
                <p class="text-xs text-zinc-500">{{ rentalDays && rentalDays > 1 ? 'Rental Days' : 'Rental Day' }}</p>
                <p class="text-sm font-medium text-zinc-900">{{ rentalDays }} day{{ rentalDays && rentalDays > 1 ? 's' : '' }}</p>
              </div>

              <hr v-if="estimatedTotal !== null" class="border-zinc-200" />

              <div v-if="estimatedTotal !== null">
                <p class="text-xs text-zinc-500">Estimated Total</p>
                <p class="text-lg font-bold text-zinc-900">â‚±{{ estimatedTotal.toLocaleString('en-PH') }}</p>
              </div>
            </div>
          </div>
        </div>
      </template>
    </main>
  </div>
</template>

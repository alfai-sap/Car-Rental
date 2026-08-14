<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute, RouterLink } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import Navbar from '@/components/Navbar.vue'
import Button from '@/components/ui/Button.vue'
import { Fuel, Users, Gauge, Car, ChevronLeft, ChevronRight, ZoomIn, ZoomOut, RotateCcw, X } from 'lucide-vue-next'
import api from '@/services/api'

const auth = useAuthStore()

interface VehicleImage {
  id: number
  image: string
  is_primary: boolean
}

interface Vehicle {
  id: number
  make: string
  model: string
  year: number
  type: string
  transmission: string
  fuel: string
  seats: number
  price_per_day: string
  status: string
  description: string
  images: VehicleImage[]
  total_units: number
  available_units: number
  discount_policy: {
    id: number
    name: string
    tiers: Array<{ min_days: number; discount_percent: string }>
  } | null
  weekly_price: string
  monthly_price: string
}

const route = useRoute()
const vehicle = ref<Vehicle | null>(null)
const loading = ref(true)
const error = ref('')

// Existing booking for this vehicle
const existingBooking = ref<{ id: number; status: string; status_display: string; booking_number: string } | null>(null)
const checkingBooking = ref(false)

// Image gallery
const currentImageIndex = ref(0)

// Lightbox
const lightboxOpen = ref(false)
const lightboxZoom = ref(1)

function openLightbox() {
  lightboxOpen.value = true
  lightboxZoom.value = 1
}

function closeLightbox() {
  lightboxOpen.value = false
  lightboxZoom.value = 1
}

function prevImage() {
  if (!vehicle.value) return
  currentImageIndex.value = (currentImageIndex.value - 1 + vehicle.value.images.length) % vehicle.value.images.length
}

function nextImage() {
  if (!vehicle.value) return
  currentImageIndex.value = (currentImageIndex.value + 1) % vehicle.value.images.length
}

function selectImage(index: number) {
  currentImageIndex.value = index
}

function zoomIn() {
  lightboxZoom.value = Math.min(lightboxZoom.value + 0.5, 5)
}

function zoomOut() {
  lightboxZoom.value = Math.max(lightboxZoom.value - 0.5, 0.5)
}

function resetZoom() {
  lightboxZoom.value = 1
}

function formatPrice(price: string): string {
  return `₱${Number(price).toLocaleString('en-PH')}/day`
}

function formatAmount(amount: string): string {
  return `₱${Number(amount).toLocaleString('en-PH')}`
}

// Discount tiers come from the vehicle detail response (server-computed via
// the vehicle's effective policy).  Used only for the tier summary text.
const discountPercentForDays = computed(() => {
  const tiers = vehicle.value?.discount_policy?.tiers ?? []
  return (days: number): number => {
    const applicable = tiers.filter(t => t.min_days <= days)
    if (applicable.length === 0) return 0
    return Number(applicable.reduce((a, b) => (b.min_days > a.min_days ? b : a)).discount_percent)
  }
})

const weeklyDiscountPercent = computed(() => discountPercentForDays.value(7))
const monthlyDiscountPercent = computed(() => discountPercentForDays.value(30))

const weeklyPrice = computed(() => {
  if (!vehicle.value) return ''
  return formatAmount(vehicle.value.weekly_price)
})

const monthlyPrice = computed(() => {
  if (!vehicle.value) return ''
  return formatAmount(vehicle.value.monthly_price)
})

onMounted(async () => {
  try {
    const id = route.params.id
    const response = await api.get(`/vehicles/${id}/`)
    vehicle.value = response.data

    // Check if user has an existing booking for this vehicle
    if (auth.isAuthenticated) {
      checkingBooking.value = true
      try {
        const bookingRes = await api.get('/bookings/', { params: { vehicle: id } })
        const userBookings: Array<{ id: number; status: string; status_display: string; booking_number: string; vehicle: number }> = bookingRes.data.results || bookingRes.data
        const active = userBookings.find(b =>
          b.vehicle === Number(id) &&
          ['pending_approval', 'approved', 'awaiting_payment', 'confirmed', 'active'].includes(b.status)
        )
        if (active) {
          const detail = await api.get(`/bookings/${active.id}/`)
          existingBooking.value = {
            id: detail.data.id,
            status: detail.data.status,
            status_display: detail.data.status_display,
            booking_number: detail.data.booking_number,
          }
        }
      } catch { /* ignore */ }
      finally { checkingBooking.value = false }
    }
  } catch {
    error.value = 'Vehicle not found.'
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="min-h-screen flex flex-col bg-zinc-50">
    <Navbar />

    <main class="flex-1 max-w-5xl mx-auto px-4 pt-24 pb-16 w-full">
      <!-- Loading -->
      <div v-if="loading" class="text-center py-20">
        <p class="text-sm text-zinc-500">Loading vehicle...</p>
      </div>

      <!-- Error -->
      <div v-else-if="error" class="text-center py-20">
        <Car class="h-12 w-12 text-zinc-300 mx-auto mb-4" />
        <p class="text-sm text-zinc-500">{{ error }}</p>
        <RouterLink to="/vehicles" class="text-sm text-zinc-900 font-medium hover:underline mt-2 inline-block">
          Back to vehicles
        </RouterLink>
      </div>

      <!-- Detail -->
      <template v-else-if="vehicle">
        <!-- Back Link -->
        <RouterLink to="/vehicles" class="inline-flex items-center gap-1 text-sm text-zinc-500 hover:text-zinc-900 mb-6">
          <ChevronLeft class="h-4 w-4" /> Back to vehicles
        </RouterLink>

        <!-- Gallery + Booking Sidebar -->
        <div class="grid grid-cols-1 lg:grid-cols-3 gap-8 mb-10">
          <!-- Image Gallery -->
          <div class="lg:col-span-2">
            <div v-if="vehicle.images.length">
              <div class="relative aspect-[16/10] bg-zinc-100 rounded-lg overflow-hidden">
                <img
                  :src="vehicle.images[currentImageIndex]?.image"
                  :alt="`${vehicle.make} ${vehicle.model}`"
                  class="w-full h-full object-cover cursor-zoom-in"
                  @click="openLightbox"
                />
                <button
                  v-if="vehicle.images.length > 1"
                  @click="prevImage"
                  class="absolute left-3 top-1/2 -translate-y-1/2 h-9 w-9 rounded-full bg-white/80 backdrop-blur-sm flex items-center justify-center hover:bg-white transition shadow-sm"
                >
                  <ChevronLeft class="h-5 w-5 text-zinc-700" />
                </button>
                <button
                  v-if="vehicle.images.length > 1"
                  @click="nextImage"
                  class="absolute right-3 top-1/2 -translate-y-1/2 h-9 w-9 rounded-full bg-white/80 backdrop-blur-sm flex items-center justify-center hover:bg-white transition shadow-sm"
                >
                  <ChevronRight class="h-5 w-5 text-zinc-700" />
                </button>
                <span v-if="vehicle.images.length > 1" class="absolute bottom-3 right-3 text-xs bg-black/60 text-white px-2 py-1 rounded-full">
                  {{ currentImageIndex + 1 }} / {{ vehicle.images.length }}
                </span>
              </div>
              <!-- Thumbnails -->
              <div v-if="vehicle.images.length > 1" class="flex gap-2 mt-3 overflow-x-auto">
                <button
                  v-for="(img, idx) in vehicle.images"
                  :key="img.id"
                  @click="selectImage(idx)"
                  class="flex-shrink-0 w-16 h-12 rounded-md overflow-hidden border-2 transition"
                  :class="idx === currentImageIndex ? 'border-zinc-900' : 'border-transparent hover:border-zinc-300'"
                >
                  <img :src="img.image" class="w-full h-full object-cover" />
                </button>
              </div>
            </div>

            <!-- No Images -->
            <div v-else class="aspect-[16/10] bg-zinc-100 rounded-lg flex items-center justify-center">
              <Car class="h-16 w-16 text-zinc-300" />
            </div>
          </div>

          <!-- Booking Sidebar -->
          <div class="rounded-lg border border-zinc-200 bg-white p-6 h-fit space-y-5">
            <!-- Price per day (primary) -->
            <div>
              
              <p class="text-3xl font-bold text-zinc-900 tracking-tight">{{ formatPrice(vehicle.price_per_day) }}</p>
            </div>

            <!-- Duration pricing -->
            <div class="grid grid-cols-2 gap-3">
              <div class="rounded-md border border-zinc-300 p-3">
                <p class="text-xs text-zinc-500 mb-1">Weekly (7 days)</p>
                <p class="text-base font-semibold text-zinc-900">{{ weeklyPrice }}</p>
                <p v-if="weeklyDiscountPercent > 0" class="text-xs text-green-700 mt-1">Save {{ weeklyDiscountPercent }}%</p>
              </div>
              <div class="rounded-md border border-zinc-300 p-3">
                <p class="text-xs text-zinc-500 mb-1">Monthly (30 days)</p>
                <p class="text-base font-semibold text-zinc-900">{{ monthlyPrice }}</p>
                <p v-if="monthlyDiscountPercent > 0" class="text-xs text-green-700 mt-1">Save {{ monthlyDiscountPercent }}%</p>
              </div>
            </div>

            <!-- Discount reminder -->
            <p class="text-xs text-zinc-400 leading-relaxed">
              Discount policies are subject to change and are applied at booking time.
            </p>

            <!-- Unit Availability -->
            <div class="rounded-md border border-zinc-300 p-3">
              <p class="text-xs text-zinc-500 mb-1">Availability</p>
              <p class="text-sm font-medium text-zinc-900">
                {{ vehicle.available_units }} of {{ vehicle.total_units }} units available
              </p>
            </div>

            <!-- Unavailable status message -->
            <div v-if="vehicle.status === 'unavailable'" class="rounded-md bg-red-50 border border-red-200 p-3 text-center">
              <p class="text-sm font-medium text-red-700 mb-1">This vehicle is currently unavailable</p>
              <p class="text-xs text-red-600">It has been marked as unavailable by the administrator and cannot be booked at this time.</p>
            </div>

            <!-- Existing booking -->
            <template v-if="checkingBooking">
              <Button class="w-full" disabled>Checking...</Button>
            </template>
            <template v-else-if="existingBooking">
              <div class="rounded-md bg-amber-50 border border-amber-200 p-3 text-center mb-3">
                <p class="text-xs text-amber-700 font-medium mb-1">You have sent a booking request for this vehicle</p>
                <p class="text-xs text-amber-600">Booking will be available again once your request is cancelled, rejected, or completed.</p>
              </div>
              <div class="rounded-md bg-zinc-50 border border-zinc-200 p-3 text-center">
                <p class="text-xs text-zinc-500 mb-1">Booking Status</p>
                <p class="text-sm font-semibold text-zinc-900">{{ existingBooking.status_display }}</p>
                <p class="text-xs text-zinc-400 mt-1">{{ existingBooking.booking_number }}</p>
              </div>
              <RouterLink :to="`/transactions/${existingBooking.id}`">
                <Button class="w-full" variant="ghost">View Transaction</Button>
              </RouterLink>
            </template>
            <template v-else>
              <RouterLink v-if="vehicle.status === 'available'" :to="`/vehicles/${vehicle.id}/book`">
                <Button class="w-full">Book Now</Button>
              </RouterLink>
              <Button v-else class="w-full" disabled>Unavailable</Button>
            </template>
          </div>
        </div>

        <!-- Main Info -->
        <div class="space-y-6">
          <div>
            <h1 class="text-2xl font-semibold text-zinc-900">{{ vehicle.make }} {{ vehicle.model }}</h1>
            <p class="text-zinc-500">{{ vehicle.year }} · {{ vehicle.type }}</p>
          </div>

          <!-- Description -->
          <div v-if="vehicle.description">
            <h2 class="text-sm font-semibold text-zinc-500 uppercase tracking-wider mb-2">Description</h2>
            <p class="text-sm text-zinc-700 leading-relaxed">{{ vehicle.description }}</p>
          </div>

          <!-- Specs -->
          <div>
            <h2 class="text-sm font-semibold text-zinc-500 uppercase tracking-wider mb-3">Specifications</h2>
            <div class="grid grid-cols-2 sm:grid-cols-3 gap-4">
              <div class="flex items-center gap-2 text-sm text-zinc-700">
                <Gauge class="h-4 w-4 text-zinc-400" />
                <span class="capitalize">{{ vehicle.transmission }}</span>
              </div>
              <div class="flex items-center gap-2 text-sm text-zinc-700">
                <Fuel class="h-4 w-4 text-zinc-400" />
                <span class="capitalize">{{ vehicle.fuel }}</span>
              </div>
              <div class="flex items-center gap-2 text-sm text-zinc-700">
                <Users class="h-4 w-4 text-zinc-400" />
                <span>{{ vehicle.seats }} seats</span>
              </div>
            </div>
          </div>
        </div>
      </template>
    </main>

    <!-- Lightbox -->
    <Teleport to="body">
      <div
        v-if="lightboxOpen"
        class="fixed inset-0 z-[100] bg-black/90 flex items-center justify-center"
        @click.self="closeLightbox"
      >
        <button @click="closeLightbox" class="absolute top-4 right-4 text-white/70 hover:text-white">
          <X class="h-6 w-6" />
        </button>
        <button @click="zoomOut" class="absolute bottom-4 left-4 text-white/70 hover:text-white">
          <ZoomOut class="h-5 w-5" />
        </button>
        <button @click="zoomIn" class="absolute bottom-4 left-16 text-white/70 hover:text-white">
          <ZoomIn class="h-5 w-5" />
        </button>
        <button @click="resetZoom" class="absolute bottom-4 left-28 text-white/70 hover:text-white">
          <RotateCcw class="h-5 w-5" />
        </button>
        <img
          v-if="vehicle?.images[currentImageIndex]"
          :src="vehicle.images[currentImageIndex]?.image"
          :style="{ transform: `scale(${lightboxZoom})`, transition: 'transform 0.2s' }"
          class="max-w-[90vw] max-h-[85vh] object-contain cursor-zoom-in"
          @click="zoomIn"
        />
        <button
          v-if="vehicle && vehicle.images.length > 1"
          @click.stop="prevImage"
          class="absolute left-4 top-1/2 -translate-y-1/2 h-10 w-10 rounded-full bg-white/20 flex items-center justify-center hover:bg-white/30"
        >
          <ChevronLeft class="h-6 w-6 text-white" />
        </button>
        <button
          v-if="vehicle && vehicle.images.length > 1"
          @click.stop="nextImage"
          class="absolute right-4 top-1/2 -translate-y-1/2 h-10 w-10 rounded-full bg-white/20 flex items-center justify-center hover:bg-white/30"
        >
          <ChevronRight class="h-6 w-6 text-white" />
        </button>
      </div>
    </Teleport>
  </div>
</template>

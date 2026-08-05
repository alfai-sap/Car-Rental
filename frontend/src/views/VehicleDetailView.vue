<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, RouterLink } from 'vue-router'
import Navbar from '@/components/Navbar.vue'
import Button from '@/components/ui/Button.vue'
import { Fuel, Users, Gauge, Car, ChevronLeft, ChevronRight, ZoomIn, ZoomOut, RotateCcw, X } from 'lucide-vue-next'
import api from '@/services/api'

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
}

const route = useRoute()
const vehicle = ref<Vehicle | null>(null)
const loading = ref(true)
const error = ref('')

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

function formatPrice(price: string): string {
  return `₱${Number(price).toLocaleString('en-PH')}/day`
}

onMounted(async () => {
  try {
    const id = route.params.id
    const response = await api.get(`/vehicles/${id}/`)
    vehicle.value = response.data
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

        <!-- Image Gallery -->
        <div v-if="vehicle.images.length" class="mb-8">
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
        <div v-else class="aspect-[16/10] bg-zinc-100 rounded-lg flex items-center justify-center mb-8">
          <Car class="h-16 w-16 text-zinc-300" />
        </div>

        <!-- Info Grid -->
        <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
          <!-- Main Info -->
          <div class="lg:col-span-2 space-y-6">
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

          <!-- Sidebar -->
          <div class="rounded-lg border border-zinc-200 bg-white p-6 h-fit space-y-4">
            <div>
              <p class="text-2xl font-bold text-zinc-900">{{ formatPrice(vehicle.price_per_day) }}</p>
              <p class="text-xs text-zinc-500 mt-1">Free cancellation up to 24 hours before pickup</p>
            </div>
            <Button class="w-full" disabled>Book Now (Coming Soon)</Button>
            <p class="text-xs text-center text-zinc-400">Booking will be available in the next update.</p>
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
        <button @click="lightboxZoom = 1" class="absolute bottom-4 left-28 text-white/70 hover:text-white">
          <RotateCcw class="h-5 w-5" />
        </button>
        <img
          v-if="vehicle?.images[currentImageIndex]"
          :src="vehicle.images[currentImageIndex].image"
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

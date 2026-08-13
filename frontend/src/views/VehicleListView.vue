<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import Navbar from '@/components/Navbar.vue'
import Input from '@/components/ui/Input.vue'
import { Search, SlidersHorizontal, Fuel, Users, Gauge, Car } from 'lucide-vue-next'
import api from '@/services/api'

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
  primary_image: string | null
}

const vehicles = ref<Vehicle[]>([])
const loading = ref(true)
const search = ref('')
const selectedType = ref('')
const selectedTransmission = ref('')
const selectedFuel = ref('')
const sortBy = ref('-created_at')

const types = ['sedan', 'suv', 'hatchback', 'mpv', 'pickup', 'van', 'coupe']
const transmissions = ['automatic', 'manual']
const fuels = ['gasoline', 'diesel', 'electric', 'hybrid']

async function fetchVehicles() {
  loading.value = true
  try {
    const params: Record<string, string> = { ordering: sortBy.value }
    if (search.value) params.search = search.value
    if (selectedType.value) params.type = selectedType.value
    if (selectedTransmission.value) params.transmission = selectedTransmission.value
    if (selectedFuel.value) params.fuel = selectedFuel.value

    const response = await api.get('/vehicles/', { params })
    vehicles.value = response.data.results
  } catch {
    vehicles.value = []
  } finally {
    loading.value = false
  }
}

function formatPrice(price: string): string {
  return `â‚±${Number(price).toLocaleString('en-PH')}/day`
}

function vehicleImage(url: string | null): string {
  return url || ''
}

onMounted(fetchVehicles)
</script>

<template>
  <div class="min-h-screen flex flex-col bg-zinc-50">
    <Navbar />

    <main class="flex-1 max-w-7xl mx-auto px-4 pt-24 pb-16 w-full">
      <div class="flex items-center justify-between mb-8">
        <div>
          <h1 class="text-2xl font-semibold text-zinc-900 tracking-tight">Available Vehicles</h1>
          <p class="text-sm text-zinc-500 mt-1">Browse our fleet and find your perfect ride.</p>
        </div>
      </div>

      <!-- Search & Filters -->
      <div class="flex flex-col sm:flex-row gap-3 mb-6">
        <div class="relative flex-1">
          <Search class="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-zinc-400" />
          <Input v-model="search" class="pl-10" placeholder="Search make, model..." @input="fetchVehicles" />
        </div>
        <select v-model="selectedType" @change="fetchVehicles"
          class="h-10 rounded-md border border-zinc-300 bg-surface px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-zinc-400">
          <option value="">All Types</option>
          <option v-for="t in types" :key="t" :value="t">{{ t }}</option>
        </select>
        <select v-model="selectedTransmission" @change="fetchVehicles"
          class="h-10 rounded-md border border-zinc-300 bg-surface px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-zinc-400">
          <option value="">All Transmissions</option>
          <option v-for="t in transmissions" :key="t" :value="t" class="capitalize">{{ t }}</option>
        </select>
        <select v-model="selectedFuel" @change="fetchVehicles"
          class="h-10 rounded-md border border-zinc-300 bg-surface px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-zinc-400">
          <option value="">All Fuel</option>
          <option v-for="f in fuels" :key="f" :value="f" class="capitalize">{{ f }}</option>
        </select>
        <select v-model="sortBy" @change="fetchVehicles"
          class="h-10 rounded-md border border-zinc-300 bg-surface px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-zinc-400">
          <option value="-created_at">Newest</option>
          <option value="price_per_day">Price: Low to High</option>
          <option value="-price_per_day">Price: High to Low</option>
          <option value="year">Year: Old to New</option>
        </select>
      </div>

      <!-- Loading -->
      <div v-if="loading" class="text-center py-20">
        <p class="text-sm text-zinc-500">Loading vehicles...</p>
      </div>

      <!-- Empty State -->
      <div v-else-if="!vehicles.length" class="text-center py-20">
        <Car class="h-12 w-12 text-zinc-300 mx-auto mb-4" />
        <p class="text-sm text-zinc-500">No vehicles match your criteria.</p>
        <button @click="search = ''; selectedType = ''; selectedTransmission = ''; selectedFuel = ''; fetchVehicles()"
          class="text-sm text-zinc-900 font-medium hover:underline mt-2">
          Clear filters
        </button>
      </div>

      <!-- Vehicle Grid -->
      <div v-else class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
        <RouterLink
          v-for="vehicle in vehicles"
          :key="vehicle.id"
          :to="`/vehicles/${vehicle.id}`"
          class="group rounded-lg border border-zinc-200 bg-surface overflow-hidden hover:border-zinc-300 hover:shadow-sm transition"
        >
          <div class="aspect-[16/10] bg-zinc-100 flex items-center justify-center overflow-hidden">
            <img
              v-if="vehicle.primary_image"
              :src="vehicle.primary_image"
              :alt="`${vehicle.make} ${vehicle.model}`"
              class="w-full h-full object-cover group-hover:scale-105 transition duration-300"
            />
            <Car v-else class="h-12 w-12 text-zinc-300" />
          </div>
          <div class="p-4">
            <div class="flex items-start justify-between gap-2">
              <div>
                <h3 class="font-semibold text-zinc-900">{{ vehicle.make }} {{ vehicle.model }}</h3>
                <p class="text-sm text-zinc-500">{{ vehicle.year }} Â· {{ vehicle.type }}</p>
              </div>
              <span class="text-sm font-semibold text-zinc-900 whitespace-nowrap">{{ formatPrice(vehicle.price_per_day) }}</span>
            </div>
            <div class="flex items-center gap-4 mt-3 text-xs text-zinc-500">
              <span class="flex items-center gap-1">
                <Gauge class="h-3.5 w-3.5" /> {{ vehicle.transmission }}
              </span>
              <span class="flex items-center gap-1">
                <Fuel class="h-3.5 w-3.5" /> {{ vehicle.fuel }}
              </span>
              <span class="flex items-center gap-1">
                <Users class="h-3.5 w-3.5" /> {{ vehicle.seats }}
              </span>
            </div>
          </div>
        </RouterLink>
      </div>
    </main>
  </div>
</template>

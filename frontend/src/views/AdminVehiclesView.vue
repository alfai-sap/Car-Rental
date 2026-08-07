<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue'
import { RouterLink } from 'vue-router'
import Navbar from '@/components/Navbar.vue'
import Button from '@/components/ui/Button.vue'
import api from '@/services/api'
import {
  Car, Plus, ChevronLeft, ChevronRight,
  Search, ListFilter, ArrowUpDown, ChevronDown,
} from 'lucide-vue-next'

interface VehicleImage {
  id: number
  image: string
  is_primary: boolean
}

interface VehicleItem {
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
  primary_image: string | null
  images: VehicleImage[]
  created_at: string
}

const loading = ref(true)
const vehicles = ref<VehicleItem[]>([])
const searchQuery = ref('')
const activeTab = ref('all')
const filterDropdownOpen = ref(false)
const sortDropdownOpen = ref(false)
const sortBy = ref('newest')
const currentPage = ref(1)
const perPage = 5

const STATUS_TABS = [
  { key: 'all', label: 'All' },
  { key: 'available', label: 'Available' },
  { key: 'rented', label: 'Rented' },
  { key: 'maintenance', label: 'Maintenance' },
]

const SORT_OPTIONS = [
  { key: 'newest', label: 'Newest First' },
  { key: 'oldest', label: 'Oldest First' },
  { key: 'price_high', label: 'Price (High to Low)' },
  { key: 'price_low', label: 'Price (Low to High)' },
]

const filteredVehicles = computed(() => {
  let result = vehicles.value
  if (activeTab.value !== 'all') {
    result = result.filter(v => v.status === activeTab.value)
  }
  if (searchQuery.value.trim()) {
    const q = searchQuery.value.toLowerCase()
    result = result.filter(v =>
      `${v.make} ${v.model}`.toLowerCase().includes(q) ||
      v.type.toLowerCase().includes(q)
    )
  }
  return result
})

const totalPages = computed(() => Math.max(1, Math.ceil(filteredVehicles.value.length / perPage)))

const sortedVehicles = computed(() => {
  const arr = [...filteredVehicles.value]
  switch (sortBy.value) {
    case 'oldest': return arr.reverse()
    case 'price_high': return arr.sort((a, b) => Number(b.price_per_day) - Number(a.price_per_day))
    case 'price_low': return arr.sort((a, b) => Number(a.price_per_day) - Number(b.price_per_day))
    default: return arr
  }
})

const paginatedVehicles = computed(() => {
  const start = (currentPage.value - 1) * perPage
  return sortedVehicles.value.slice(start, start + perPage)
})

watch(activeTab, () => { currentPage.value = 1 })
watch(searchQuery, () => { currentPage.value = 1 })

function selectFilter(key: string) {
  activeTab.value = key
  filterDropdownOpen.value = false
}

function selectSort(key: string) {
  sortBy.value = key
  sortDropdownOpen.value = false
  currentPage.value = 1
}

function goToPage(page: number) {
  currentPage.value = Math.max(1, Math.min(page, totalPages.value))
}

async function fetchVehicles() {
  loading.value = true
  try {
    const response = await api.get('/vehicles/')
    vehicles.value = response.data.results || response.data
  } catch {
    // ignore
  } finally {
    loading.value = false
  }
}

function formatPrice(price: string): string {
  return `₱${Number(price).toLocaleString('en-PH')}/day`
}

function statusBadgeClass(status: string): string {
  switch (status) {
    case 'available': return 'bg-green-100 text-green-800'
    case 'rented': return 'bg-blue-100 text-blue-800'
    case 'maintenance': return 'bg-amber-100 text-amber-800'
    case 'retired': return 'bg-zinc-100 text-zinc-500'
    default: return 'bg-zinc-100 text-zinc-800'
  }
}

onMounted(fetchVehicles)
</script>

<template>
  <div class="min-h-screen flex flex-col bg-zinc-50">
    <Navbar />

    <main class="flex-1 max-w-6xl mx-auto px-4 pt-24 pb-16 w-full">
      <div class="flex items-center justify-between mb-8">
        <div>
          <h1 class="text-2xl font-semibold text-zinc-900">Vehicle Management</h1>
          <p class="text-sm text-zinc-500 mt-1">Manage vehicle listings and inventory.</p>
        </div>
        <div class="flex items-center gap-2">
          <RouterLink to="/admin/dashboard" class="text-sm text-zinc-500 hover:text-zinc-900">
            Dashboard
          </RouterLink>
          <span class="text-zinc-300">/</span>
          <span class="text-sm text-zinc-900 font-medium">Vehicles</span>
        </div>
      </div>

      <!-- Toolbar -->
      <div class="flex items-center gap-3 mb-6 flex-wrap">
        <div class="relative flex-1 max-w-xs">
          <Search class="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-zinc-400" />
          <input
            v-model="searchQuery"
            type="text"
            placeholder="Search vehicles..."
            class="h-9 w-full rounded-md border border-zinc-300 bg-white pl-9 pr-3 text-sm placeholder:text-zinc-400 focus:outline-none focus:ring-2 focus:ring-zinc-400"
          />
        </div>

        <div class="relative">
          <button
            @click="filterDropdownOpen = !filterDropdownOpen"
            class="flex items-center gap-2 h-9 px-3 rounded-md border border-zinc-300 bg-white text-sm text-zinc-700 hover:bg-zinc-50"
          >
            <ListFilter class="h-4 w-4 text-zinc-400" />
            <span>{{ STATUS_TABS.find(t => t.key === activeTab)?.label || 'All' }}</span>
            <ChevronDown class="h-3.5 w-3.5 text-zinc-400" />
          </button>
          <div
            v-if="filterDropdownOpen"
            class="absolute left-0 mt-1 w-40 rounded-md border border-zinc-200 bg-white shadow-lg z-30"
            @mouseleave="filterDropdownOpen = false"
          >
            <div class="p-1">
              <button
                v-for="tab in STATUS_TABS"
                :key="tab.key"
                @click="selectFilter(tab.key)"
                class="w-full text-left px-3 py-1.5 text-sm rounded hover:bg-zinc-100"
                :class="activeTab === tab.key ? 'text-zinc-900 font-medium bg-zinc-50' : 'text-zinc-600'"
              >
                {{ tab.label }}
              </button>
            </div>
          </div>
        </div>

        <div class="relative">
          <button
            @click="sortDropdownOpen = !sortDropdownOpen"
            class="flex items-center gap-2 h-9 px-3 rounded-md border border-zinc-300 bg-white text-sm text-zinc-700 hover:bg-zinc-50"
          >
            <ArrowUpDown class="h-4 w-4 text-zinc-400" />
            <span>{{ SORT_OPTIONS.find(o => o.key === sortBy)?.label || 'Sort' }}</span>
            <ChevronDown class="h-3.5 w-3.5 text-zinc-400" />
          </button>
          <div
            v-if="sortDropdownOpen"
            class="absolute left-0 mt-1 w-44 rounded-md border border-zinc-200 bg-white shadow-lg z-30"
            @mouseleave="sortDropdownOpen = false"
          >
            <div class="p-1">
              <button
                v-for="opt in SORT_OPTIONS"
                :key="opt.key"
                @click="selectSort(opt.key)"
                class="w-full text-left px-3 py-1.5 text-sm rounded hover:bg-zinc-100"
                :class="sortBy === opt.key ? 'text-zinc-900 font-medium bg-zinc-50' : 'text-zinc-600'"
              >
                {{ opt.label }}
              </button>
            </div>
          </div>
        </div>

        <div class="flex-1" />

        <Button @click="openCreateForm">
          <Plus class="h-4 w-4 mr-1" /> Add Vehicle
        </Button>
      </div>

      <!-- Loading -->
      <div v-if="loading" class="text-center py-20">
        <p class="text-sm text-zinc-500">Loading vehicles...</p>
      </div>

      <!-- Empty state -->
      <div v-else-if="vehicles.length === 0" class="text-center py-16">
        <div class="inline-flex items-center justify-center w-16 h-16 rounded-full bg-zinc-100 mb-4">
          <Car class="h-8 w-8 text-zinc-400" />
        </div>
        <h2 class="text-lg font-medium text-zinc-900 mb-2">No vehicles yet</h2>
        <p class="text-sm text-zinc-500 mb-6">Add your first vehicle listing to get started.</p>
        <Button @click="openCreateForm">Add Vehicle</Button>
      </div>

      <template v-else>
        <div v-if="paginatedVehicles.length === 0" class="text-center py-12">
          <p class="text-sm text-zinc-500">No vehicles match this filter.</p>
        </div>

        <div class="space-y-3">
          <RouterLink
            v-for="vehicle in paginatedVehicles"
            :key="vehicle.id"
            :to="`/admin/vehicles/${vehicle.id}`"
            class="block rounded-md border border-zinc-200 bg-white p-4 hover:border-zinc-400 transition-colors cursor-pointer"
          >
            <div class="flex items-start gap-4">
              <div class="h-16 w-24 rounded-md bg-zinc-100 overflow-hidden flex-shrink-0">
                <img
                  v-if="vehicle.primary_image"
                  :src="vehicle.primary_image"
                  :alt="`${vehicle.make} ${vehicle.model}`"
                  class="h-full w-full object-cover"
                />
                <div v-else class="h-full w-full flex items-center justify-center">
                  <Car class="h-6 w-6 text-zinc-400" />
                </div>
              </div>

              <div class="flex-1 min-w-0">
                <div class="flex items-center gap-2 mb-0.5">
                  <p class="text-sm font-medium text-zinc-900">{{ vehicle.make }} {{ vehicle.model }}</p>
                  <span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium" :class="statusBadgeClass(vehicle.status)">
                    {{ vehicle.status.charAt(0).toUpperCase() + vehicle.status.slice(1) }}
                  </span>
                </div>
                <p class="text-xs text-zinc-500">{{ vehicle.year }} · {{ vehicle.type }} · {{ vehicle.transmission }} · {{ vehicle.fuel }} · {{ vehicle.seats }} seats</p>
                <p class="text-sm font-medium text-zinc-800 mt-1">{{ formatPrice(vehicle.price_per_day) }}</p>
              </div>
            </div>
          </RouterLink>
        </div>

        <!-- Pagination -->
        <div v-if="totalPages > 1" class="flex items-center justify-center gap-2 mt-6">
          <button
            @click="goToPage(currentPage - 1)"
            :disabled="currentPage === 1"
            class="h-8 w-8 flex items-center justify-center rounded text-zinc-500 hover:text-zinc-900 disabled:opacity-30 disabled:cursor-default"
          >
            <ChevronLeft class="h-4 w-4" />
          </button>
          <button
            v-for="page in totalPages"
            :key="page"
            @click="goToPage(page)"
            class="h-8 w-8 flex items-center justify-center rounded text-xs font-medium transition-colors"
            :class="page === currentPage ? 'bg-zinc-900 text-white' : 'text-zinc-600 hover:bg-zinc-100'"
          >
            {{ page }}
          </button>
          <button
            @click="goToPage(currentPage + 1)"
            :disabled="currentPage === totalPages"
            class="h-8 w-8 flex items-center justify-center rounded text-zinc-500 hover:text-zinc-900 disabled:opacity-30 disabled:cursor-default"
          >
            <ChevronRight class="h-4 w-4" />
          </button>
        </div>
      </template>
    </main>
  </div>
</template>

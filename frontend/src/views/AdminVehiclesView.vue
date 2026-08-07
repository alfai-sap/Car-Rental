<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue'
import { RouterLink } from 'vue-router'
import Navbar from '@/components/Navbar.vue'
import Button from '@/components/ui/Button.vue'
import api from '@/services/api'
import {
  Car, Plus, Pencil, Trash2, X, ChevronLeft, ChevronRight,
  Search, ListFilter, ArrowUpDown, ChevronDown, Package,
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
  units?: VehicleUnit[]
}

interface VehicleUnit {
  id: number
  vehicle: number
  vehicle_name: string
  plate_number: string
  status: string
  mileage: number
  notes: string
  created_at: string
  updated_at: string
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

const showForm = ref(false)
const editingVehicle = ref<VehicleItem | null>(null)
const formLoading = ref(false)
const formError = ref('')
const deleteConfirmId = ref<number | null>(null)

// Unit management
const showUnitManager = ref(false)
const unitVehicle = ref<VehicleItem | null>(null)
const unitLoading = ref(false)
const unitForm = ref({ plate_number: '', status: 'available', mileage: 0, notes: '' })
const showUnitForm = ref(false)
const editingUnit = ref<VehicleUnit | null>(null)
const unitFormError = ref('')
const unitFormLoading = ref(false)
const deleteUnitId = ref<number | null>(null)

const form = ref({
  make: '',
  model: '',
  year: new Date().getFullYear(),
  type: 'Sedan',
  transmission: 'automatic',
  fuel: 'gasoline',
  seats: 5,
  price_per_day: '',
  status: 'available',
  description: '',
})

const imageFiles = ref<File[]>([])
const imagePreviews = ref<string[]>([])

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

function openCreateForm() {
  editingVehicle.value = null
  form.value = {
    make: '',
    model: '',
    year: new Date().getFullYear(),
    type: 'Sedan',
    transmission: 'automatic',
    fuel: 'gasoline',
    seats: 5,
    price_per_day: '',
    status: 'available',
    description: '',
  }
  imageFiles.value = []
  imagePreviews.value = []
  formError.value = ''
  showForm.value = true
}

function openEditForm(vehicle: VehicleItem) {
  editingVehicle.value = vehicle
  form.value = {
    make: vehicle.make,
    model: vehicle.model,
    year: vehicle.year,
    type: vehicle.type,
    transmission: vehicle.transmission,
    fuel: vehicle.fuel,
    seats: vehicle.seats,
    price_per_day: vehicle.price_per_day,
    status: vehicle.status,
    description: vehicle.description,
  }
  imageFiles.value = []
  imagePreviews.value = []
  formError.value = ''
  showForm.value = true
}

function closeForm() {
  showForm.value = false
  editingVehicle.value = null
  formError.value = ''
}

function handleImageSelect(event: Event) {
  const input = event.target as HTMLInputElement
  if (!input.files) return
  imageFiles.value = Array.from(input.files)
  imagePreviews.value = imageFiles.value.map(f => URL.createObjectURL(f))
}

async function submitForm() {
  formError.value = ''
  formLoading.value = true

  try {
    const payload = new FormData()
    payload.append('make', form.value.make)
    payload.append('model', form.value.model)
    payload.append('year', String(form.value.year))
    payload.append('type', form.value.type)
    payload.append('transmission', form.value.transmission)
    payload.append('fuel', form.value.fuel)
    payload.append('seats', String(form.value.seats))
    payload.append('price_per_day', form.value.price_per_day)
    payload.append('status', form.value.status)
    payload.append('description', form.value.description)

    imageFiles.value.forEach(file => {
      payload.append('uploaded_images', file)
    })

    if (editingVehicle.value) {
      await api.put(`/vehicles/${editingVehicle.value.id}/`, payload, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      for (const file of imageFiles.value) {
        const imgForm = new FormData()
        imgForm.append('image', file)
        imgForm.append('is_primary', 'false')
        await api.post(`/vehicles/${editingVehicle.value.id}/images/`, imgForm, {
          headers: { 'Content-Type': 'multipart/form-data' },
        })
      }
    } else {
      await api.post('/vehicles/', payload, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
    }

    closeForm()
    await fetchVehicles()
  } catch (error: any) {
    formError.value = error?.response?.data
      ? Object.values(error.response.data).flat().join(', ')
      : 'Failed to save vehicle.'
  } finally {
    formLoading.value = false
  }
}

async function deleteVehicle(id: number) {
  try {
    await api.delete(`/vehicles/${id}/`)
    deleteConfirmId.value = null
    await fetchVehicles()
  } catch {
    // ignore
  }
}

// ── Unit management ──

async function openUnitManager(vehicle: VehicleItem) {
  unitVehicle.value = vehicle
  showUnitManager.value = true
  await fetchUnits()
}

function closeUnitManager() {
  showUnitManager.value = false
  unitVehicle.value = null
}

async function fetchUnits() {
  if (!unitVehicle.value) return
  unitLoading.value = true
  try {
    const response = await api.get(`/vehicles/${unitVehicle.value.id}/units/`)
    unitVehicle.value.units = response.data.results || response.data
  } catch { /* ignore */ }
  finally { unitLoading.value = false }
}

function openAddUnit() {
  editingUnit.value = null
  unitForm.value = { plate_number: '', status: 'available', mileage: 0, notes: '' }
  unitFormError.value = ''
  showUnitForm.value = true
}

function openEditUnit(unit: VehicleUnit) {
  editingUnit.value = unit
  unitForm.value = {
    plate_number: unit.plate_number,
    status: unit.status,
    mileage: unit.mileage,
    notes: unit.notes,
  }
  unitFormError.value = ''
  showUnitForm.value = true
}

function closeUnitForm() {
  showUnitForm.value = false
  editingUnit.value = null
  unitFormError.value = ''
}

async function submitUnitForm() {
  if (!unitVehicle.value) return
  unitFormError.value = ''
  unitFormLoading.value = true
  try {
    const payload = { ...unitForm.value }
    if (editingUnit.value) {
      await api.put(`/vehicles/${unitVehicle.value.id}/units/${editingUnit.value.id}/`, payload)
    } else {
      await api.post(`/vehicles/${unitVehicle.value.id}/units/`, payload)
    }
    closeUnitForm()
    await fetchUnits()
    await fetchVehicles()
  } catch (error: any) {
    unitFormError.value = error?.response?.data
      ? Object.values(error.response.data).flat().join(', ')
      : 'Failed to save unit.'
  } finally {
    unitFormLoading.value = false
  }
}

async function deleteUnit(unitId: number) {
  if (!unitVehicle.value) return
  try {
    await api.delete(`/vehicles/${unitVehicle.value.id}/units/${unitId}/`)
    deleteUnitId.value = null
    await fetchUnits()
    await fetchVehicles()
  } catch { /* ignore */ }
}

function unitStatusBadge(status: string): string {
  switch (status) {
    case 'available': return 'bg-green-100 text-green-800'
    case 'reserved': return 'bg-amber-100 text-amber-800'
    case 'booked': return 'bg-blue-100 text-blue-800'
    case 'active_rental': return 'bg-emerald-100 text-emerald-800'
    case 'maintenance': return 'bg-red-100 text-red-800'
    case 'inactive': return 'bg-zinc-100 text-zinc-500'
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
          <div
            v-for="vehicle in paginatedVehicles"
            :key="vehicle.id"
            class="rounded-md border border-zinc-200 bg-white p-4"
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

              <div class="flex items-center gap-1 flex-shrink-0">
                <Button variant="ghost" size="sm" @click="openUnitManager(vehicle)">
                  <Package class="h-4 w-4" />
                </Button>
                <Button variant="ghost" size="sm" @click="openEditForm(vehicle)">
                  <Pencil class="h-4 w-4" />
                </Button>
                <Button variant="ghost" size="sm" @click="deleteConfirmId = vehicle.id">
                  <Trash2 class="h-4 w-4 text-red-500" />
                </Button>
              </div>
            </div>
          </div>
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

    <!-- Create / Edit Modal -->
    <Teleport to="body">
      <div
        v-if="showForm"
        class="fixed inset-0 z-[200] flex items-start justify-center pt-16 p-4 overflow-y-auto"
      >
        <div class="absolute inset-0 bg-black/50" @click="closeForm" />
        <div class="relative bg-white rounded-lg shadow-xl max-w-lg w-full p-6 space-y-4">
          <div class="flex items-center justify-between">
            <h3 class="text-lg font-semibold text-zinc-900">
              {{ editingVehicle ? 'Edit Vehicle' : 'Add Vehicle' }}
            </h3>
            <button @click="closeForm" class="text-zinc-400 hover:text-zinc-600">
              <X class="h-5 w-5" />
            </button>
          </div>

          <p v-if="formError" class="text-sm text-red-600 bg-red-50 rounded-md px-3 py-2">{{ formError }}</p>

          <div class="grid grid-cols-2 gap-3">
            <div class="space-y-1">
              <label class="text-xs font-medium text-zinc-700">Make</label>
              <input v-model="form.make" placeholder="Toyota" class="h-9 w-full rounded-md border border-zinc-300 bg-white px-3 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-zinc-400" />
            </div>
            <div class="space-y-1">
              <label class="text-xs font-medium text-zinc-700">Model</label>
              <input v-model="form.model" placeholder="Vios" class="h-9 w-full rounded-md border border-zinc-300 bg-white px-3 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-zinc-400" />
            </div>
          </div>

          <div class="grid grid-cols-3 gap-3">
            <div class="space-y-1">
              <label class="text-xs font-medium text-zinc-700">Year</label>
              <input v-model.number="form.year" type="number" class="h-9 w-full rounded-md border border-zinc-300 bg-white px-3 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-zinc-400" />
            </div>
            <div class="space-y-1">
              <label class="text-xs font-medium text-zinc-700">Type</label>
              <select v-model="form.type" class="h-9 w-full rounded-md border border-zinc-300 bg-white px-3 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-zinc-400">
                <option>Sedan</option>
                <option>SUV</option>
                <option>Hatchback</option>
                <option>Van</option>
                <option>Truck</option>
                <option>Coupe</option>
                <option>Convertible</option>
              </select>
            </div>
            <div class="space-y-1">
              <label class="text-xs font-medium text-zinc-700">Seats</label>
              <input v-model.number="form.seats" type="number" min="1" max="20" class="h-9 w-full rounded-md border border-zinc-300 bg-white px-3 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-zinc-400" />
            </div>
          </div>

          <div class="grid grid-cols-2 gap-3">
            <div class="space-y-1">
              <label class="text-xs font-medium text-zinc-700">Transmission</label>
              <select v-model="form.transmission" class="h-9 w-full rounded-md border border-zinc-300 bg-white px-3 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-zinc-400">
                <option value="automatic">Automatic</option>
                <option value="manual">Manual</option>
              </select>
            </div>
            <div class="space-y-1">
              <label class="text-xs font-medium text-zinc-700">Fuel</label>
              <select v-model="form.fuel" class="h-9 w-full rounded-md border border-zinc-300 bg-white px-3 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-zinc-400">
                <option value="gasoline">Gasoline</option>
                <option value="diesel">Diesel</option>
                <option value="electric">Electric</option>
                <option value="hybrid">Hybrid</option>
              </select>
            </div>
          </div>

          <div class="grid grid-cols-2 gap-3">
            <div class="space-y-1">
              <label class="text-xs font-medium text-zinc-700">Price Per Day (₱)</label>
              <input v-model="form.price_per_day" type="number" min="0" step="0.01" placeholder="1500.00" class="h-9 w-full rounded-md border border-zinc-300 bg-white px-3 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-zinc-400" />
            </div>
            <div class="space-y-1">
              <label class="text-xs font-medium text-zinc-700">Status</label>
              <select v-model="form.status" class="h-9 w-full rounded-md border border-zinc-300 bg-white px-3 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-zinc-400">
                <option value="available">Available</option>
                <option value="rented">Rented</option>
                <option value="maintenance">Maintenance</option>
                <option value="retired">Retired</option>
              </select>
            </div>
          </div>

          <div class="space-y-1">
            <label class="text-xs font-medium text-zinc-700">Description</label>
            <textarea v-model="form.description" rows="3" placeholder="Vehicle description..." class="w-full rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm placeholder:text-zinc-400 focus:outline-none focus:ring-2 focus:ring-zinc-400" />
          </div>

          <div class="space-y-1">
            <label class="text-xs font-medium text-zinc-700">Images</label>
            <input
              type="file"
              accept="image/*"
              multiple
              @change="handleImageSelect"
              class="block w-full text-sm text-zinc-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-medium file:bg-zinc-100 file:text-zinc-700 hover:file:bg-zinc-200"
            />
            <div v-if="editingVehicle && editingVehicle.images.length && imagePreviews.length === 0" class="text-xs text-zinc-400 mt-1">
              {{ editingVehicle.images.length }} existing image(s). Upload new ones to add more.
            </div>
            <div v-if="imagePreviews.length" class="flex gap-2 mt-2 flex-wrap">
              <img
                v-for="(preview, idx) in imagePreviews"
                :key="idx"
                :src="preview"
                class="h-16 w-20 object-cover rounded-md border border-zinc-200"
              />
            </div>
          </div>

          <div class="flex gap-2 pt-2">
            <Button variant="ghost" class="flex-1" @click="closeForm">Cancel</Button>
            <Button class="flex-1" :disabled="formLoading" @click="submitForm">
              {{ formLoading ? 'Saving...' : editingVehicle ? 'Update Vehicle' : 'Add Vehicle' }}
            </Button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Delete Confirmation Modal -->
    <Teleport to="body">
      <div
        v-if="deleteConfirmId !== null"
        class="fixed inset-0 z-[200] flex items-center justify-center p-4"
      >
        <div class="absolute inset-0 bg-black/50" @click="deleteConfirmId = null" />
        <div class="relative bg-white rounded-lg shadow-xl max-w-sm w-full p-6 space-y-4">
          <h3 class="text-lg font-semibold text-zinc-900">Delete Vehicle</h3>
          <p class="text-sm text-zinc-500">
            Are you sure you want to delete this vehicle? This action cannot be undone.
          </p>
          <div class="flex gap-2 pt-2">
            <Button variant="ghost" class="flex-1" @click="deleteConfirmId = null">Cancel</Button>
            <Button class="flex-1 bg-red-600 hover:bg-red-700 text-white" @click="deleteVehicle(deleteConfirmId!)">
              Delete
            </Button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- ===== Unit Manager Modal ===== -->
    <Teleport to="body">
      <div
        v-if="showUnitManager && unitVehicle"
        class="fixed inset-0 z-[200] flex items-start justify-center pt-16 p-4 overflow-y-auto"
      >
        <div class="absolute inset-0 bg-black/50" @click="closeUnitManager" />
        <div class="relative bg-white rounded-lg shadow-xl max-w-lg w-full p-6 space-y-4">
          <div class="flex items-center justify-between">
            <div>
              <h3 class="text-lg font-semibold text-zinc-900">Manage Units</h3>
              <p class="text-sm text-zinc-500">{{ unitVehicle.make }} {{ unitVehicle.model }}</p>
            </div>
            <button @click="closeUnitManager" class="text-zinc-400 hover:text-zinc-600">
              <X class="h-5 w-5" />
            </button>
          </div>

          <div v-if="unitLoading" class="text-center py-8">
            <p class="text-sm text-zinc-500">Loading units...</p>
          </div>

          <template v-else>
            <table v-if="unitVehicle.units && unitVehicle.units.length > 0" class="w-full text-sm">
              <thead>
                <tr class="border-b border-zinc-200 text-left text-xs text-zinc-400 uppercase">
                  <th class="pb-2 font-medium">Plate</th>
                  <th class="pb-2 font-medium">Status</th>
                  <th class="pb-2 font-medium">Mileage</th>
                  <th class="pb-2 font-medium text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="unit in unitVehicle.units" :key="unit.id" class="border-b border-zinc-100">
                  <td class="py-2 font-mono text-zinc-900">{{ unit.plate_number }}</td>
                  <td class="py-2">
                    <span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium" :class="unitStatusBadge(unit.status)">
                      {{ unit.status.replace('_', ' ').replace(/\b\w/g, c => c.toUpperCase()) }}
                    </span>
                  </td>
                  <td class="py-2 text-zinc-600">{{ unit.mileage?.toLocaleString() || '—' }} km</td>
                  <td class="py-2 text-right">
                    <Button variant="ghost" size="sm" @click="openEditUnit(unit)"><Pencil class="h-3.5 w-3.5" /></Button>
                    <Button variant="ghost" size="sm" @click="deleteUnitId = unit.id"><Trash2 class="h-3.5 w-3.5 text-red-500" /></Button>
                  </td>
                </tr>
              </tbody>
            </table>
            <p v-else class="text-sm text-zinc-500 text-center py-4">No units added yet.</p>
          </template>

          <Button class="w-full" variant="ghost" @click="openAddUnit">
            <Plus class="h-4 w-4 mr-1" /> Add Unit
          </Button>
        </div>
      </div>
    </Teleport>

    <!-- ===== Add/Edit Unit Form Modal ===== -->
    <Teleport to="body">
      <div
        v-if="showUnitForm"
        class="fixed inset-0 z-[210] flex items-start justify-center pt-20 p-4"
      >
        <div class="absolute inset-0 bg-black/60" @click="closeUnitForm" />
        <div class="relative bg-white rounded-lg shadow-xl max-w-sm w-full p-6 space-y-4">
          <div class="flex items-center justify-between">
            <h3 class="text-lg font-semibold text-zinc-900">
              {{ editingUnit ? 'Edit Unit' : 'Add Unit' }}
            </h3>
            <button @click="closeUnitForm" class="text-zinc-400 hover:text-zinc-600"><X class="h-5 w-5" /></button>
          </div>

          <p v-if="unitFormError" class="text-sm text-red-600 bg-red-50 rounded-md px-3 py-2">{{ unitFormError }}</p>

          <div class="space-y-3">
            <div class="space-y-1">
              <label class="text-xs font-medium text-zinc-700">Plate Number</label>
              <input v-model="unitForm.plate_number" placeholder="ABC-1234" class="h-9 w-full rounded-md border border-zinc-300 bg-white px-3 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-zinc-400" />
            </div>
            <div class="space-y-1">
              <label class="text-xs font-medium text-zinc-700">Status</label>
              <select v-model="unitForm.status" class="h-9 w-full rounded-md border border-zinc-300 bg-white px-3 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-zinc-400">
                <option value="available">Available</option>
                <option value="reserved">Reserved</option>
                <option value="booked">Booked</option>
                <option value="active_rental">Active Rental</option>
                <option value="maintenance">Maintenance</option>
                <option value="inactive">Inactive</option>
              </select>
            </div>
            <div class="space-y-1">
              <label class="text-xs font-medium text-zinc-700">Mileage (km)</label>
              <input v-model.number="unitForm.mileage" type="number" min="0" class="h-9 w-full rounded-md border border-zinc-300 bg-white px-3 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-zinc-400" />
            </div>
            <div class="space-y-1">
              <label class="text-xs font-medium text-zinc-700">Notes</label>
              <textarea v-model="unitForm.notes" rows="2" placeholder="Optional notes..." class="w-full rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm placeholder:text-zinc-400 focus:outline-none focus:ring-2 focus:ring-zinc-400" />
            </div>
          </div>

          <div class="flex gap-2 pt-2">
            <Button variant="ghost" class="flex-1" @click="closeUnitForm">Cancel</Button>
            <Button class="flex-1" :disabled="unitFormLoading" @click="submitUnitForm">
              {{ unitFormLoading ? 'Saving...' : editingUnit ? 'Update Unit' : 'Add Unit' }}
            </Button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- ===== Delete Unit Confirmation ===== -->
    <Teleport to="body">
      <div
        v-if="deleteUnitId !== null"
        class="fixed inset-0 z-[210] flex items-center justify-center p-4"
      >
        <div class="absolute inset-0 bg-black/50" @click="deleteUnitId = null" />
        <div class="relative bg-white rounded-lg shadow-xl max-w-sm w-full p-6 space-y-4">
          <h3 class="text-lg font-semibold text-zinc-900">Delete Unit</h3>
          <p class="text-sm text-zinc-500">Are you sure you want to remove this vehicle unit?</p>
          <div class="flex gap-2 pt-2">
            <Button variant="ghost" class="flex-1" @click="deleteUnitId = null">Cancel</Button>
            <Button class="flex-1 bg-red-600 hover:bg-red-700 text-white" @click="deleteUnit(deleteUnitId!)">Delete</Button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

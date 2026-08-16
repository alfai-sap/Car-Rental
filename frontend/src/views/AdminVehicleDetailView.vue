<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter, RouterLink } from 'vue-router'
import Navbar from '@/components/Navbar.vue'
import Button from '@/components/ui/Button.vue'
import api from '@/services/api'
import {
  Car, Pencil, Trash2, ChevronLeft, Plus, X,
  Save, Upload, Package,
} from 'lucide-vue-next'

const route = useRoute()
const router = useRouter()

interface VehicleImage {
  id: number
  image: string
  is_primary: boolean
  uploaded_at: string
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
  created_at: string
  updated_at: string
  units?: VehicleUnit[]
}

const vehicle = ref<Vehicle | null>(null)
const loading = ref(true)
const error = ref('')
const saveError = ref('')
const saving = ref(false)
const currentImage = ref(0)

// ── Image gallery ──
function prevImage() {
  if (!vehicle.value) return
  currentImage.value = (currentImage.value - 1 + vehicle.value.images.length) % vehicle.value.images.length
}
function nextImage() {
  if (!vehicle.value) return
  currentImage.value = (currentImage.value + 1) % vehicle.value.images.length
}

// ── Edit mode for vehicle info ──
const editingInfo = ref(false)
const editForm = ref({
  make: '', model: '', year: 0, type: '', transmission: '', fuel: '',
  seats: 0, price_per_day: '', description: '', status: 'available',
})

// ── Unit management ──
const units = ref<VehicleUnit[]>([])
const unitsLoading = ref(false)
const showUnitForm = ref(false)
const editingUnit = ref<VehicleUnit | null>(null)
const unitForm = ref({ plate_number: '', status: 'available', mileage: 0, notes: '' })
const unitFormError = ref('')
const unitFormLoading = ref(false)
const deleteUnitId = ref<number | null>(null)
const deleteUnitError = ref('')

// ── Delete vehicle ──
const showDeleteConfirm = ref(false)
const deleting = ref(false)
const deleteError = ref('')

const isNew = computed(() => route.params.id === 'new')

async function fetchVehicle() {
  if (isNew.value) {
    vehicle.value = {
      id: 0, make: '', model: '', year: new Date().getFullYear(),
      type: 'sedan', transmission: 'automatic', fuel: 'gasoline',
      seats: 5, price_per_day: '', status: 'available', description: '',
      images: [], created_at: '', updated_at: '',
    }
    loading.value = false
    return
  }
  loading.value = true
  try {
    const response = await api.get(`/vehicles/${route.params.id}/`)
    vehicle.value = response.data
  } catch {
    error.value = 'Vehicle not found.'
  } finally {
    loading.value = false
  }
}

async function fetchUnits() {
  if (isNew.value) { unitsLoading.value = false; return }
  unitsLoading.value = true
  try {
    const response = await api.get(`/vehicles/${route.params.id}/units/`)
    units.value = response.data.results || response.data
  } catch { /* ignore */ }
  finally { unitsLoading.value = false }
}

onMounted(async () => {
  await fetchVehicle()
  await fetchUnits()
})

// ── Edit vehicle info ──
function startEditInfo() {
  if (!vehicle.value) return
  editForm.value = {
    make: vehicle.value.make,
    model: vehicle.value.model,
    year: vehicle.value.year,
    type: vehicle.value.type,
    transmission: vehicle.value.transmission,
    fuel: vehicle.value.fuel,
    seats: vehicle.value.seats,
    price_per_day: vehicle.value.price_per_day,
    description: vehicle.value.description,
    status: vehicle.value.status,
  }
  editingInfo.value = true
}

function cancelEditInfo() {
  editingInfo.value = false
  saveError.value = ''
}

// ── Save vehicle info ──
async function saveVehicleInfo() {
  saving.value = true
  saveError.value = ''
  try {
    const payload: Record<string, any> = {
      make: editForm.value.make,
      model: editForm.value.model,
      year: editForm.value.year,
      type: editForm.value.type,
      transmission: editForm.value.transmission,
      fuel: editForm.value.fuel,
      seats: editForm.value.seats,
      price_per_day: editForm.value.price_per_day,
      description: editForm.value.description,
      status: editForm.value.status,
    }
    if (isNew.value) {
      const response = await api.post('/vehicles/', payload)
      router.push({ name: 'admin-vehicle-detail', params: { id: response.data.id } })
    } else {
      await api.put(`/vehicles/${route.params.id}/`, payload)
      editingInfo.value = false
      await fetchVehicle()
    }
  } catch (e: any) {
    const data = e?.response?.data
    const status = e?.response?.status
    if (status === 403) {
      saveError.value = 'You do not have permission. Please log in again.'
    } else if (typeof data === 'string' && (data.startsWith('<!') || data.startsWith('<html'))) {
      saveError.value = 'An unexpected error occurred. Please try again.'
    } else if (typeof data === 'string') {
      saveError.value = data
    } else if (data && typeof data === 'object') {
      const messages: string[] = []
      for (const [, errors] of Object.entries(data)) {
        if (Array.isArray(errors)) messages.push(...errors.filter((v): v is string => typeof v === 'string'))
        else if (typeof errors === 'string') messages.push(errors)
      }
      saveError.value = messages.length > 0 ? messages.join('. ') : 'Failed to save.'
    } else {
      saveError.value = 'Failed to save.'
    }
  } finally {
    saving.value = false
  }
}

async function deleteVehicle() {
  if (isNew.value) return
  deleting.value = true
  deleteError.value = ''
  try {
    await api.delete(`/vehicles/${route.params.id}/`)
    router.push({ name: 'admin-vehicles' })
  } catch (e: any) {
    deleteError.value = e?.response?.data?.detail || 'Unable to delete this vehicle.'
  } finally { deleting.value = false }
}

// ── Unit CRUD ──
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
  unitFormError.value = ''
  unitFormLoading.value = true
  try {
    const payload: Record<string, any> = {
      plate_number: unitForm.value.plate_number,
      status: unitForm.value.status,
      mileage: unitForm.value.mileage || 0,
      notes: unitForm.value.notes,
    }
    if (editingUnit.value) {
      await api.put(`/vehicles/${route.params.id}/units/${editingUnit.value.id}/`, payload)
    } else {
      await api.post(`/vehicles/${route.params.id}/units/`, payload)
    }
    closeUnitForm()
    await fetchUnits()
  } catch (e: any) {
    unitFormError.value = e?.response?.data
      ? Object.values(e.response.data).flat().join(', ')
      : 'Failed to save unit.'
  } finally {
    unitFormLoading.value = false
  }
}

async function deleteUnit(unitId: number) {
  deleteUnitError.value = ''
  try {
    await api.delete(`/vehicles/${route.params.id}/units/${unitId}/`)
    deleteUnitId.value = null
    await fetchUnits()
  } catch (e: any) {
    deleteUnitError.value = e?.response?.data?.detail || 'Unable to delete this unit.'
  }
}

async function deleteImage(imageId: number) {
  try {
    await api.delete(`/vehicles/${route.params.id}/images/${imageId}/`)
    await fetchVehicle()
  } catch { /* ignore */ }
}

async function handleImageUpload(event: Event) {
  const input = event.target as HTMLInputElement
  if (!input.files?.length) return
  for (const file of Array.from(input.files)) {
    const fd = new FormData()
    fd.append('image', file)
    fd.append('is_primary', 'false')
    try {
      await api.post(`/vehicles/${route.params.id}/images/`, fd, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
    } catch { /* ignore */ }
  }
  await fetchVehicle()
  input.value = ''
}

function formatPrice(price: string): string {
  return `₱${Number(price).toLocaleString('en-PH')}/day`
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
</script>

<template>
  <div class="min-h-screen flex flex-col bg-zinc-50">
    <Navbar />

    <main class="flex-1 max-w-6xl mx-auto px-4 pt-24 pb-16 w-full">
      <!-- Breadcrumb -->
      <div class="flex items-center gap-2 mb-6">
        <RouterLink to="/admin/vehicles" class="text-sm text-zinc-500 hover:text-zinc-900 flex items-center gap-1">
          <ChevronLeft class="h-3.5 w-3.5" /> Vehicles
        </RouterLink>
      </div>

      <!-- Loading -->
      <div v-if="loading" class="text-center py-20">
        <p class="text-sm text-zinc-500">Loading vehicle...</p>
      </div>

      <!-- Error -->
      <div v-else-if="error" class="text-center py-20">
        <p class="text-sm text-red-600">{{ error }}</p>
        <RouterLink to="/admin/vehicles" class="text-sm text-zinc-500 hover:text-zinc-900 mt-2 inline-block">
          Back to vehicles
        </RouterLink>
      </div>

      <template v-else-if="vehicle">
        <!-- Two Column Layout -->
        <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <!-- LEFT COLUMN: Vehicle Info (2/3 width) -->
          <div class="lg:col-span-2 space-y-6">
            <!-- Image Gallery -->
            <div class="rounded-lg border border-zinc-200 bg-white overflow-hidden">
              <template v-if="vehicle.images.length">
                <div class="aspect-video bg-zinc-900 relative">
                  <img
                    :src="vehicle.images[currentImage]?.image"
                    :alt="`${vehicle.make} ${vehicle.model} photo ${currentImage + 1}`"
                    class="h-full w-full object-contain"
                  />
                  <button
                    v-if="vehicle.images.length > 1"
                    @click="prevImage"
                    class="absolute left-2 top-1/2 -translate-y-1/2 h-10 w-10 rounded-full bg-black/40 hover:bg-black/60 flex items-center justify-center text-white transition"
                  >
                    <ChevronLeft class="h-5 w-5" />
                  </button>
                  <button
                    v-if="vehicle.images.length > 1"
                    @click="nextImage"
                    class="absolute right-2 top-1/2 -translate-y-1/2 h-10 w-10 rounded-full bg-black/40 hover:bg-black/60 flex items-center justify-center text-white transition"
                  >
                    <ChevronRight class="h-5 w-5" />
                  </button>
                  <span class="absolute bottom-3 right-3 bg-black/50 text-white text-xs rounded px-2 py-0.5">
                    {{ currentImage + 1 }} / {{ vehicle.images.length }}
                  </span>
                </div>
              </template>
              <div v-else class="aspect-video bg-zinc-100 flex items-center justify-center">
                <Car class="h-16 w-16 text-zinc-300" />
              </div>
              <div v-if="vehicle.images.length > 1" class="flex gap-2 p-3 overflow-x-auto">
                <button
                  v-for="(img, idx) in vehicle.images"
                  :key="img.id"
                  @click="currentImage = idx"
                  class="h-14 w-20 flex-shrink-0 overflow-hidden rounded border-2 transition"
                  :class="idx === currentImage ? 'border-zinc-900' : 'border-zinc-200 hover:border-zinc-400'"
                >
                  <img :src="img.image" class="h-full w-full object-cover" />
                </button>
              </div>
            </div>

            <!-- Vehicle Details -->
            <div class="rounded-lg border border-zinc-200 bg-white p-6">
              <div class="flex items-center justify-between mb-4">
                <h2 class="text-lg font-semibold text-zinc-900">Vehicle Details</h2>
                <div class="flex gap-1">
                  <Button v-if="!editingInfo" variant="ghost" size="sm" @click="startEditInfo">
                    <Pencil class="h-4 w-4 mr-1" /> Edit
                  </Button>
                  <Button variant="ghost" size="sm" @click="showDeleteConfirm = true">
                    <Trash2 class="h-4 w-4 mr-1 text-red-500" /> Delete
                  </Button>
                </div>
              </div>

              <!-- View Mode -->
              <div v-if="!editingInfo" class="space-y-3">
                <div class="flex items-center gap-2">
                  <h3 class="text-xl font-semibold text-zinc-900">{{ vehicle.year }} {{ vehicle.make }} {{ vehicle.model }}</h3>
                  <span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium capitalize"
                    :class="vehicle.status === 'available' ? 'bg-green-100 text-green-800' : 'bg-zinc-100 text-zinc-800'">
                    {{ vehicle.status }}
                  </span>
                </div>
                <p class="text-sm text-zinc-500">{{ vehicle.description }}</p>
                <div class="grid grid-cols-2 sm:grid-cols-3 gap-2 pt-2">
                  <div class="bg-zinc-50 rounded-md p-3">
                    <p class="text-xs text-zinc-400">Type</p>
                    <p class="text-sm font-medium text-zinc-900">{{ vehicle.type }}</p>
                  </div>
                  <div class="bg-zinc-50 rounded-md p-3">
                    <p class="text-xs text-zinc-400">Transmission</p>
                    <p class="text-sm font-medium text-zinc-900 capitalize">{{ vehicle.transmission }}</p>
                  </div>
                  <div class="bg-zinc-50 rounded-md p-3">
                    <p class="text-xs text-zinc-400">Fuel</p>
                    <p class="text-sm font-medium text-zinc-900 capitalize">{{ vehicle.fuel }}</p>
                  </div>
                  <div class="bg-zinc-50 rounded-md p-3">
                    <p class="text-xs text-zinc-400">Seats</p>
                    <p class="text-sm font-medium text-zinc-900">{{ vehicle.seats }}</p>
                  </div>
                  <div class="bg-zinc-50 rounded-md p-3">
                    <p class="text-xs text-zinc-400">Price</p>
                    <p class="text-sm font-medium text-zinc-900">{{ formatPrice(vehicle.price_per_day) }}</p>
                  </div>
                </div>
              </div>

              <!-- Edit Mode -->
              <div v-else class="space-y-4">
                <p v-if="saveError" class="text-sm text-red-600 bg-red-50 rounded-md px-3 py-2">{{ saveError }}</p>

                <div class="grid grid-cols-2 gap-3">
                  <div class="space-y-1">
                    <label class="text-xs font-medium text-zinc-700">Make</label>
                    <input v-model="editForm.make" class="h-9 w-full rounded-md border border-zinc-300 bg-white px-3 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-zinc-400" />
                  </div>
                  <div class="space-y-1">
                    <label class="text-xs font-medium text-zinc-700">Model</label>
                    <input v-model="editForm.model" class="h-9 w-full rounded-md border border-zinc-300 bg-white px-3 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-zinc-400" />
                  </div>
                </div>

                <div class="grid grid-cols-3 gap-3">
                  <div class="space-y-1">
                    <label class="text-xs font-medium text-zinc-700">Year</label>
                    <input v-model.number="editForm.year" type="number" class="h-9 w-full rounded-md border border-zinc-300 bg-white px-3 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-zinc-400" />
                  </div>
                  <div class="space-y-1">
                    <label class="text-xs font-medium text-zinc-700">Type</label>
                    <select v-model="editForm.type" class="h-9 w-full rounded-md border border-zinc-300 bg-white px-3 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-zinc-400">
                      <option value="sedan">Sedan</option><option value="suv">SUV</option><option value="hatchback">Hatchback</option><option value="mpv">MPV</option><option value="van">Van</option><option value="pickup">Pickup</option><option value="truck">Truck</option><option value="coupe">Coupe</option>
                    </select>
                  </div>
                  <div class="space-y-1">
                    <label class="text-xs font-medium text-zinc-700">Status</label>
                    <select v-model="editForm.status" class="h-9 w-full rounded-md border border-zinc-300 bg-white px-3 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-zinc-400">
                      <option value="available">Available</option>
                      <option value="unavailable">Unavailable</option>
                    </select>
                  </div>
                </div>

                <div class="grid grid-cols-2 gap-3">
                  <div class="space-y-1">
                    <label class="text-xs font-medium text-zinc-700">Seats</label>
                    <input v-model.number="editForm.seats" type="number" min="1" max="20" class="h-9 w-full rounded-md border border-zinc-300 bg-white px-3 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-zinc-400" />
                  </div>
                </div>

                <div class="grid grid-cols-2 gap-3">
                  <div class="space-y-1">
                    <label class="text-xs font-medium text-zinc-700">Transmission</label>
                    <select v-model="editForm.transmission" class="h-9 w-full rounded-md border border-zinc-300 bg-white px-3 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-zinc-400">
                      <option value="automatic">Automatic</option><option value="manual">Manual</option>
                    </select>
                  </div>
                  <div class="space-y-1">
                    <label class="text-xs font-medium text-zinc-700">Fuel</label>
                    <select v-model="editForm.fuel" class="h-9 w-full rounded-md border border-zinc-300 bg-white px-3 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-zinc-400">
                      <option value="gasoline">Gasoline</option><option value="diesel">Diesel</option><option value="electric">Electric</option><option value="hybrid">Hybrid</option>
                    </select>
                  </div>
                </div>

                <div class="space-y-1">
                  <label class="text-xs font-medium text-zinc-700">Price Per Day (₱)</label>
                  <input v-model="editForm.price_per_day" type="number" min="0" step="0.01" class="h-9 w-full rounded-md border border-zinc-300 bg-white px-3 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-zinc-400" />
                </div>

                <div class="space-y-1">
                  <label class="text-xs font-medium text-zinc-700">Description</label>
                  <textarea v-model="editForm.description" rows="3" class="w-full rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-zinc-400" />
                </div>

                <!-- Image management during edit -->
                <div class="space-y-2">
                  <label class="text-xs font-medium text-zinc-700">Images</label>
                  <div v-if="vehicle.images.length" class="flex gap-2 flex-wrap mb-2">
                    <div v-for="img in vehicle.images" :key="img.id" class="relative group h-16 w-20 flex-shrink-0 rounded overflow-hidden border border-zinc-200">
                      <img :src="img.image" class="h-full w-full object-cover" />
                      <button
                        @click="deleteImage(img.id)"
                        class="absolute inset-0 bg-red-500/70 flex items-center justify-center opacity-0 group-hover:opacity-100 transition"
                        title="Delete image"
                      >
                        <Trash2 class="h-4 w-4 text-white" />
                      </button>
                    </div>
                  </div>
                  <input
                    type="file"
                    accept="image/*"
                    multiple
                    @change="handleImageUpload"
                    class="block w-full text-sm text-zinc-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-medium file:bg-zinc-100 file:text-zinc-700 hover:file:bg-zinc-200"
                  />
                </div>

                <div class="flex gap-2 pt-2">
                  <Button variant="ghost" @click="cancelEditInfo">Cancel</Button>
                  <Button :disabled="saving" @click="saveVehicleInfo">
                    <Save class="h-4 w-4 mr-1" /> {{ saving ? 'Saving...' : 'Save Changes' }}
                  </Button>
                </div>
              </div>
            </div>

            <!-- Unit Management -->
            <div class="rounded-lg border border-zinc-200 bg-white p-6">
              <div class="flex items-center justify-between mb-4">
                <h2 class="text-lg font-semibold text-zinc-900">Vehicle Units</h2>
                <Button variant="ghost" size="sm" @click="openAddUnit">
                  <Plus class="h-4 w-4 mr-1" /> Add Unit
                </Button>
              </div>

              <div v-if="unitsLoading" class="text-center py-4">
                <p class="text-sm text-zinc-500">Loading units...</p>
              </div>

              <div v-else-if="units.length === 0" class="text-center py-8">
                <Package class="h-10 w-10 text-zinc-300 mx-auto mb-2" />
                <p class="text-sm text-zinc-500">No units added yet.</p>
                <p class="text-xs text-zinc-400 mt-1">Add at least one unit for this vehicle to be bookable.</p>
              </div>

              <table v-else class="w-full text-sm">
                <thead>
                  <tr class="border-b border-zinc-200 text-left text-xs text-zinc-400 uppercase">
                    <th class="pb-2 font-medium">Plate Number</th>
                    <th class="pb-2 font-medium">Status</th>
                    <th class="pb-2 font-medium">Mileage</th>
                    <th class="pb-2 font-medium">Notes</th>
                    <th class="pb-2 font-medium text-right">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="unit in units" :key="unit.id" class="border-b border-zinc-100">
                    <td class="py-2.5 font-mono text-zinc-900">{{ unit.plate_number }}</td>
                    <td class="py-2.5">
                      <span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium" :class="unitStatusBadge(unit.status)">
                        {{ unit.status.replace('_', ' ').replace(/\b\w/g, c => c.toUpperCase()) }}
                      </span>
                    </td>
                    <td class="py-2.5 text-zinc-600">{{ unit.mileage?.toLocaleString() || '—' }} km</td>
                    <td class="py-2.5 text-zinc-500 text-xs max-w-[120px] truncate">{{ unit.notes || '—' }}</td>
                    <td class="py-2.5 text-right">
                      <Button variant="ghost" size="sm" @click="openEditUnit(unit)">
                        <Pencil class="h-3.5 w-3.5" />
                      </Button>
                      <Button variant="ghost" size="sm" @click="deleteUnitId = unit.id">
                        <Trash2 class="h-3.5 w-3.5 text-red-500" />
                      </Button>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          <!-- RIGHT COLUMN: Summary Card (1/3 width) -->
          <div class="space-y-4">
            <div class="rounded-lg border border-zinc-200 bg-white p-5 sticky top-24">
              <h3 class="text-sm font-semibold text-zinc-900 mb-3">Summary</h3>
              <div class="space-y-2 text-sm">
                <div class="flex justify-between">
                  <span class="text-zinc-500">Total Units</span>
                  <span class="font-medium text-zinc-900">{{ units.length }}</span>
                </div>
                <div class="flex justify-between">
                  <span class="text-zinc-500">Available</span>
                  <span class="font-medium text-green-700">{{ units.filter(u => u.status === 'available').length }}</span>
                </div>
                <div class="flex justify-between">
                  <span class="text-zinc-500">Booked</span>
                  <span class="font-medium text-blue-700">{{ units.filter(u => u.status === 'booked').length }}</span>
                </div>
                <div class="flex justify-between">
                  <span class="text-zinc-500">Maintenance</span>
                  <span class="font-medium text-amber-700">{{ units.filter(u => u.status === 'maintenance').length }}</span>
                </div>
                <hr class="border-zinc-100" />
                <div class="flex justify-between">
                  <span class="text-zinc-500">Created</span>
                  <span class="text-xs text-zinc-500">{{ new Date(vehicle.created_at).toLocaleDateString('en-PH') }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </template>
    </main>

    <!-- Delete vehicle confirm -->
    <Teleport to="body">
      <div v-if="showDeleteConfirm" class="fixed inset-0 z-[200] flex items-center justify-center p-4">
        <div class="absolute inset-0 bg-black/50" @click="showDeleteConfirm = false" />
        <div class="relative bg-white rounded-lg shadow-xl max-w-sm w-full p-6 space-y-4">
          <h3 class="text-lg font-semibold text-zinc-900">Delete Vehicle</h3>
          <p class="text-sm text-zinc-500">Are you sure? This will also delete all associated units and images.</p>
          <p v-if="deleteError" class="text-sm text-red-600 bg-red-50 rounded-md px-3 py-2">{{ deleteError }}</p>
          <div class="flex gap-2 pt-2">
            <Button variant="ghost" class="flex-1" @click="showDeleteConfirm = false">Cancel</Button>
            <Button class="flex-1 bg-red-600 hover:bg-red-700 text-white" :disabled="deleting" @click="deleteVehicle">
              {{ deleting ? 'Deleting...' : 'Delete' }}
            </Button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Delete unit confirm -->
    <Teleport to="body">
      <div v-if="deleteUnitId !== null" class="fixed inset-0 z-[210] flex items-center justify-center p-4">
        <div class="absolute inset-0 bg-black/50" @click="deleteUnitId = null" />
        <div class="relative bg-white rounded-lg shadow-xl max-w-sm w-full p-6 space-y-4">
          <h3 class="text-lg font-semibold text-zinc-900">Delete Unit</h3>
          <p class="text-sm text-zinc-500">Are you sure you want to remove this unit?</p>
          <p v-if="deleteUnitError" class="text-sm text-red-600 bg-red-50 rounded-md px-3 py-2">{{ deleteUnitError }}</p>
          <div class="flex gap-2 pt-2">
            <Button variant="ghost" class="flex-1" @click="deleteUnitId = null">Cancel</Button>
            <Button class="flex-1 bg-red-600 hover:bg-red-700 text-white" @click="deleteUnit(deleteUnitId!)">Delete</Button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Unit Add/Edit Modal -->
    <Teleport to="body">
      <div v-if="showUnitForm" class="fixed inset-0 z-[210] flex items-start justify-center pt-20 p-4">
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
              <input v-model="unitForm.mileage" type="number" min="0" class="h-9 w-full rounded-md border border-zinc-300 bg-white px-3 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-zinc-400" />
            </div>
            <div class="space-y-1">
              <label class="text-xs font-medium text-zinc-700">Notes</label>
              <textarea v-model="unitForm.notes" rows="2" placeholder="Optional notes..." class="w-full rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm placeholder:text-zinc-400 focus:outline-none focus:ring-2 focus:ring-zinc-400" />
            </div>
          </div>

          <div class="flex gap-2 pt-2">
            <Button variant="ghost" class="flex-1" @click="closeUnitForm">Cancel</Button>
            <Button class="flex-1" :disabled="unitFormLoading" @click="submitUnitForm">
              {{ unitFormLoading ? 'Saving...' : editingUnit ? 'Update' : 'Add' }}
            </Button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue'
import { useAuthStore } from '@/stores/auth'
import Navbar from '@/components/Navbar.vue'
import Button from '@/components/ui/Button.vue'
import api from '@/services/api'
import {
  Search, ChevronLeft, ChevronRight, Shield, Clock, User, FileText,
  CheckCircle, XCircle, CreditCard, Car, RefreshCw, AlertCircle,
  ListFilter, ArrowUpDown, Hash, Calendar,
} from 'lucide-vue-next'

const auth = useAuthStore()

// ── Types ──
interface AuditActor {
  id: number
  name: string
  email: string
}

interface AuditBooking {
  id: number
  booking_number: string
}

interface AuditPayment {
  id: number
  payment_number: string
}

interface AuditEntry {
  id: number
  action: string
  action_display: string
  summary: string
  actor: AuditActor
  booking: AuditBooking | null
  payment: AuditPayment | null
  before_state: Record<string, any>
  after_state: Record<string, any>
  ip_address: string | null
  created_at: string
}

interface ActionStats {
  [key: string]: number
}

// ── State ──
const loading = ref(true)
const error = ref('')
const entries = ref<AuditEntry[]>([])
const actionStats = ref<ActionStats>({})
const totalCount = ref(0)
const currentPage = ref(1)
const totalPages = ref(1)
const pageSize = ref(20)

// Filters
const searchQuery = ref('')
const selectedActions = ref<string[]>([])
const filterDropdownOpen = ref(false)
const sortDropdownOpen = ref(false)
const sortOrder = ref<'newest' | 'oldest'>('newest')

const ACTION_OPTIONS = [
  { key: 'booking_approved', label: 'Booking Approved', icon: CheckCircle },
  { key: 'booking_rejected', label: 'Booking Rejected', icon: XCircle },
  { key: 'payment_confirmed', label: 'Payment Confirmed', icon: CreditCard },
  { key: 'rental_activated', label: 'Rental Activated', icon: Car },
  { key: 'rental_completed', label: 'Rental Completed', icon: CheckCircle },
  { key: 'unit_assigned', label: 'Unit Assigned', icon: Hash },
  { key: 'unit_changed', label: 'Unit Changed', icon: RefreshCw },
  { key: 'booking_cancelled', label: 'Booking Cancelled', icon: XCircle },
  { key: 'booking_marked_waiting', label: 'Marked Waiting', icon: Clock },
]

// ── Fetch ──
async function fetchLogs() {
  loading.value = true
  error.value = ''
  try {
    const params: Record<string, string | number> = {
      page: currentPage.value,
      page_size: pageSize.value,
    }
    if (searchQuery.value.trim()) {
      params.search = searchQuery.value.trim()
    }
    if (selectedActions.value.length > 0) {
      params.action = selectedActions.value.join(',')
    }

    const response = await api.get('/admin/audit-logs/', { params })
    entries.value = response.data.results
    actionStats.value = response.data.action_stats
    totalCount.value = response.data.count
    totalPages.value = response.data.total_pages
  } catch (e: any) {
    error.value = e?.response?.data?.detail || 'Failed to load audit logs.'
  } finally {
    loading.value = false
  }
}

onMounted(fetchLogs)

watch([currentPage, searchQuery, sortOrder], () => {
  currentPage.value = 1  // reset on filter change
  fetchLogs()
})

watch(selectedActions, () => {
  currentPage.value = 1
  fetchLogs()
}, { deep: true })

// ── Helpers ──
function toggleActionFilter(key: string) {
  const idx = selectedActions.value.indexOf(key)
  if (idx >= 0) {
    selectedActions.value.splice(idx, 1)
  } else {
    selectedActions.value.push(key)
  }
}

function clearFilters() {
  searchQuery.value = ''
  selectedActions.value = []
  currentPage.value = 1
}

const hasActiveFilters = computed(() =>
  searchQuery.value.trim() !== '' || selectedActions.value.length > 0,
)

function goToPage(page: number) {
  currentPage.value = Math.max(1, Math.min(page, totalPages.value))
  fetchLogs()
}

function formatDateTime(isoStr: string): string {
  return new Date(isoStr).toLocaleString('en-US', {
    month: 'short', day: 'numeric', year: 'numeric',
    hour: '2-digit', minute: '2-digit', second: '2-digit',
  })
}

function getActionBadgeClass(action: string): string {
  switch (action) {
    case 'booking_approved': return 'bg-emerald-100 text-emerald-800'
    case 'booking_rejected': return 'bg-red-100 text-red-800'
    case 'payment_confirmed': return 'bg-violet-100 text-violet-800'
    case 'rental_activated': return 'bg-blue-100 text-blue-800'
    case 'rental_completed': return 'bg-zinc-100 text-zinc-700'
    case 'unit_assigned': return 'bg-cyan-100 text-cyan-800'
    case 'unit_changed': return 'bg-amber-100 text-amber-800'
    case 'booking_cancelled': return 'bg-rose-100 text-rose-800'
    case 'booking_marked_waiting': return 'bg-indigo-100 text-indigo-800'
    default: return 'bg-zinc-100 text-zinc-700'
  }
}

function getActionIcon(action: string) {
  const opt = ACTION_OPTIONS.find(o => o.key === action)
  return opt?.icon || Shield
}

const totalActionsToday = computed(() =>
  Object.values(actionStats.value).reduce((sum, c) => sum + c, 0),
)
</script>

<template>
  <Navbar />

  <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-24 pb-12">
    <!-- Header -->
    <div class="flex items-center justify-between mb-6">
      <div>
        <h1 class="text-2xl font-semibold text-zinc-900">Audit Log</h1>
        <p class="text-sm text-zinc-500 mt-1">
          Track all admin actions across the system
        </p>
      </div>
      <div class="hidden sm:flex items-center gap-3 px-4 py-2 rounded-lg bg-zinc-100 text-sm text-zinc-600">
        <Clock class="w-4 h-4" />
        <span>{{ totalActionsToday }} actions recorded</span>
      </div>
    </div>

    <!-- Search & Filter Bar -->
    <div class="flex flex-col sm:flex-row gap-3 mb-6">
      <!-- Search -->
      <div class="relative flex-1">
        <Search class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-400" />
        <input
          v-model="searchQuery"
          type="text"
          placeholder="Search by booking number, admin email, or summary..."
          class="w-full pl-10 pr-4 py-2.5 border border-zinc-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-zinc-900 focus:border-transparent"
          @keyup.enter="currentPage = 1; fetchLogs()"
        />
      </div>

      <!-- Action Filter Dropdown -->
      <div class="relative">
        <button
          @click="filterDropdownOpen = !filterDropdownOpen"
          class="flex items-center gap-2 px-4 py-2.5 border rounded-lg text-sm text-zinc-700 hover:bg-zinc-50 transition-colors"
          :class="selectedActions.length > 0 ? 'border-zinc-900 bg-zinc-50' : 'border-zinc-300'"
        >
          <ListFilter class="w-4 h-4" />
          <span>Action</span>
          <span v-if="selectedActions.length > 0" class="ml-1 px-1.5 py-0.5 rounded-full bg-zinc-900 text-white text-xs">
            {{ selectedActions.length }}
          </span>
        </button>

        <div
          v-if="filterDropdownOpen"
          class="absolute right-0 top-full mt-1 w-56 bg-white border border-zinc-200 rounded-lg shadow-lg z-50 py-1"
        >
          <div
            v-for="opt in ACTION_OPTIONS"
            :key="opt.key"
            @click="toggleActionFilter(opt.key)"
            class="flex items-center gap-3 px-3 py-2 text-sm cursor-pointer hover:bg-zinc-50"
            :class="selectedActions.includes(opt.key) ? 'text-zinc-900 font-medium' : 'text-zinc-600'"
          >
            <component :is="opt.icon" class="w-4 h-4" />
            <span class="flex-1">{{ opt.label }}</span>
            <span v-if="actionStats[opt.key]" class="text-xs text-zinc-400">{{ actionStats[opt.key] }}</span>
            <CheckCircle v-if="selectedActions.includes(opt.key)" class="w-4 h-4 text-zinc-900 ml-1" />
          </div>
          <div v-if="selectedActions.length > 0" class="border-t border-zinc-100 mt-1 pt-1 px-3">
            <button @click="selectedActions = []; filterDropdownOpen = false" class="text-xs text-zinc-500 hover:text-zinc-700">
              Clear filter
            </button>
          </div>
        </div>
      </div>

      <!-- Clear Filters -->
      <button
        v-if="hasActiveFilters"
        @click="clearFilters"
        class="px-3 py-2 text-sm text-zinc-500 hover:text-zinc-700 transition-colors"
      >
        Clear all
      </button>
    </div>

    <!-- Active Filter Chips -->
    <div v-if="selectedActions.length > 0" class="flex flex-wrap gap-2 mb-4">
      <span
        v-for="key in selectedActions"
        :key="key"
        class="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium border cursor-pointer hover:bg-zinc-100"
        :class="getActionBadgeClass(key)"
        @click="toggleActionFilter(key)"
      >
        <component :is="getActionIcon(key)" class="w-3 h-3" />
        {{ ACTION_OPTIONS.find(o => o.key === key)?.label || key }}
        <XCircle class="w-3 h-3 ml-1" />
      </span>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="flex justify-center py-16">
      <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-zinc-900" />
    </div>

    <!-- Error -->
    <div v-else-if="error" class="text-center py-16">
      <AlertCircle class="w-10 h-10 text-zinc-300 mx-auto mb-3" />
      <p class="text-zinc-500">{{ error }}</p>
      <Button variant="outline" size="sm" class="mt-4" @click="fetchLogs">Retry</Button>
    </div>

    <!-- Empty -->
    <div v-else-if="entries.length === 0" class="text-center py-16">
      <Shield class="w-10 h-10 text-zinc-200 mx-auto mb-3" />
      <p class="text-zinc-500">No audit log entries found.</p>
      <p v-if="hasActiveFilters" class="text-sm text-zinc-400 mt-1">Try adjusting your filters.</p>
    </div>

    <!-- Table -->
    <div v-else class="bg-white border border-zinc-200 rounded-lg overflow-hidden">
      <table class="w-full text-sm">
        <thead>
          <tr class="border-b border-zinc-200 bg-zinc-50 text-left">
            <th class="px-4 py-3 font-medium text-zinc-500 text-xs uppercase tracking-wider">Action</th>
            <th class="px-4 py-3 font-medium text-zinc-500 text-xs uppercase tracking-wider">Details</th>
            <th class="px-4 py-3 font-medium text-zinc-500 text-xs uppercase tracking-wider hidden md:table-cell">Admin</th>
            <th class="px-4 py-3 font-medium text-zinc-500 text-xs uppercase tracking-wider hidden lg:table-cell">Booking</th>
            <th class="px-4 py-3 font-medium text-zinc-500 text-xs uppercase tracking-wider hidden xl:table-cell">State Change</th>
            <th class="px-4 py-3 font-medium text-zinc-500 text-xs uppercase tracking-wider text-right">Time</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="entry in entries"
            :key="entry.id"
            class="border-b border-zinc-100 hover:bg-zinc-50/50 transition-colors"
          >
            <!-- Action Badge -->
            <td class="px-4 py-3">
              <span
                class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium"
                :class="getActionBadgeClass(entry.action)"
              >
                <component :is="getActionIcon(entry.action)" class="w-3.5 h-3.5" />
                {{ entry.action_display }}
              </span>
            </td>

            <!-- Summary -->
            <td class="px-4 py-3">
              <p class="text-zinc-800 font-medium truncate max-w-xs">{{ entry.summary }}</p>
              <p v-if="entry.ip_address" class="text-xs text-zinc-400 mt-0.5 flex items-center gap-1">
                <span class="inline-block w-1.5 h-1.5 rounded-full bg-zinc-300" />
                IP: {{ entry.ip_address }}
              </p>
            </td>

            <!-- Admin -->
            <td class="px-4 py-3 hidden md:table-cell">
              <div class="flex items-center gap-2">
                <div class="w-7 h-7 rounded-full bg-zinc-200 flex items-center justify-center">
                  <User class="w-3.5 h-3.5 text-zinc-500" />
                </div>
                <div>
                  <p class="text-zinc-800 text-xs font-medium">{{ entry.actor.name }}</p>
                  <p class="text-zinc-400 text-xs">{{ entry.actor.email }}</p>
                </div>
              </div>
            </td>

            <!-- Booking -->
            <td class="px-4 py-3 hidden lg:table-cell">
              <span v-if="entry.booking" class="inline-flex items-center gap-1.5 text-xs">
                <FileText class="w-3.5 h-3.5 text-zinc-400" />
                <RouterLink
                  :to="`/admin/transactions/${entry.booking.id}`"
                  class="text-zinc-700 hover:text-zinc-900 hover:underline font-mono"
                >
                  {{ entry.booking.booking_number }}
                </RouterLink>
              </span>
              <span v-else class="text-xs text-zinc-300">—</span>
            </td>

            <!-- State Change -->
            <td class="px-4 py-3 hidden xl:table-cell">
              <div class="flex items-center gap-2 text-xs">
                <span v-if="Object.keys(entry.before_state).length" class="text-zinc-500">
                  {{ Object.entries(entry.before_state).map(([k, v]) => `${k}: ${v}`).join(', ') }}
                </span>
                <span v-else class="text-zinc-300">—</span>
                <span class="text-zinc-300">→</span>
                <span v-if="Object.keys(entry.after_state).length" class="text-zinc-700 font-medium">
                  {{ Object.entries(entry.after_state).map(([k, v]) => `${k}: ${v}`).join(', ') }}
                </span>
                <span v-else class="text-zinc-300">—</span>
              </div>
            </td>

            <!-- Time -->
            <td class="px-4 py-3 text-right">
              <span class="text-xs text-zinc-500 whitespace-nowrap">
                {{ formatDateTime(entry.created_at) }}
              </span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Pagination -->
    <div v-if="totalPages > 1" class="flex items-center justify-between mt-6">
      <p class="text-sm text-zinc-500">
        Showing {{ ((currentPage - 1) * pageSize) + 1 }}–{{ Math.min(currentPage * pageSize, totalCount) }}
        of {{ totalCount }} entries
      </p>
      <div class="flex items-center gap-1">
        <button
          :disabled="currentPage <= 1"
          @click="goToPage(currentPage - 1)"
          class="p-2 rounded-md border border-zinc-200 text-zinc-600 hover:bg-zinc-50 disabled:opacity-30 disabled:cursor-not-allowed"
        >
          <ChevronLeft class="w-4 h-4" />
        </button>

        <button
          v-for="page in totalPages"
          :key="page"
          @click="goToPage(page)"
          class="px-3 py-1.5 rounded-md text-sm border transition-colors"
          :class="page === currentPage
            ? 'bg-zinc-900 text-white border-zinc-900'
            : 'border-zinc-200 text-zinc-600 hover:bg-zinc-50'"
        >
          {{ page }}
        </button>

        <button
          :disabled="currentPage >= totalPages"
          @click="goToPage(currentPage + 1)"
          class="p-2 rounded-md border border-zinc-200 text-zinc-600 hover:bg-zinc-50 disabled:opacity-30 disabled:cursor-not-allowed"
        >
          <ChevronRight class="w-4 h-4" />
        </button>
      </div>
    </div>
  </main>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import Navbar from '@/components/Navbar.vue'
import Button from '@/components/ui/Button.vue'
import Input from '@/components/ui/Input.vue'
import Label from '@/components/ui/Label.vue'
import api from '@/services/api'
import { Percent, Plus, Trash2, Save, AlertCircle, BadgeCheck } from 'lucide-vue-next'

interface Tier {
  id?: number
  min_days: string
  discount_percent: string
}

interface Policy {
  id: number
  name: string
  description: string
  is_default: boolean
  tiers: Tier[]
}

const loading = ref(true)
const saving = ref(false)
const error = ref('')
const success = ref('')

const policies = ref<Policy[]>([])
const defaultPolicyId = ref<number | null>(null)

// Editable draft of the (single) global policy
const name = ref('Global Rental Discount Policy')
const description = ref('')
const tiers = ref<Tier[]>([])

const editingPolicyId = ref<number | null>(null)

async function fetchPolicies() {
  loading.value = true
  error.value = ''
  try {
    const response = await api.get('/admin/discount-policy/')
    policies.value = response.data.policies
    defaultPolicyId.value = response.data.default_policy_id

    const existingDefault = policies.value.find(p => p.id === defaultPolicyId.value)
    if (existingDefault) {
      editingPolicyId.value = existingDefault.id
      name.value = existingDefault.name
      description.value = existingDefault.description
      tiers.value = existingDefault.tiers.map(t => ({
        id: t.id,
        min_days: String(t.min_days),
        discount_percent: Number(t.discount_percent).toString(),
      }))
    } else if (policies.value.length > 0) {
      const first = policies.value[0]!
      editingPolicyId.value = first.id
      name.value = first.name
      description.value = first.description
      tiers.value = first.tiers.map(t => ({
        id: t.id,
        min_days: String(t.min_days),
        discount_percent: Number(t.discount_percent).toString(),
      }))
    } else {
      // No policy yet — seed the standard defaults
      editingPolicyId.value = null
      name.value = 'Global Rental Discount Policy'
      description.value = 'Fleet-wide duration-based discount.'
      tiers.value = [
        { min_days: '1', discount_percent: '0' },
        { min_days: '7', discount_percent: '10' },
        { min_days: '30', discount_percent: '20' },
      ]
    }
  } catch (e: unknown) {
    error.value = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Failed to load discount policy.'
  } finally {
    loading.value = false
  }
}

onMounted(fetchPolicies)

function addTier() {
  const nextMinDays = tiers.value.length > 0
    ? Math.max(...tiers.value.map(t => Number(t.min_days))) + 1
    : 1
  tiers.value.push({ min_days: String(nextMinDays), discount_percent: '0' })
}

function removeTier(index: number) {
  tiers.value.splice(index, 1)
}

const tiersLabel = computed(() => {
  const sorted = [...tiers.value].sort((a, b) => Number(a.min_days) - Number(b.min_days))
  return sorted.map(t => `${t.min_days}+ days → ${t.discount_percent}%`).join('  ·  ')
})

async function savePolicy() {
  saving.value = true
  error.value = ''
  success.value = ''
  try {
    const payload = {
      id: editingPolicyId.value ?? undefined,
      name: name.value,
      description: description.value,
      is_default: true,
      tiers: tiers.value.map(t => ({
        min_days: Number(t.min_days),
        discount_percent: Number(t.discount_percent),
      })),
    }
    await api.post('/admin/discount-policy/', payload)
    success.value = 'Discount policy saved.'
    await fetchPolicies()
  } catch (e: unknown) {
    const data = (e as { response?: { data?: Record<string, string | string[]> | { detail?: string } } })?.response?.data
    if (data && typeof data === 'object') {
      if ('detail' in data) {
        error.value = data.detail as string
      } else {
        error.value = Object.values(data).flat().filter(Boolean).join(' ')
      }
    } else {
      error.value = 'Failed to save discount policy.'
    }
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="min-h-screen flex flex-col bg-zinc-50">
    <Navbar />

    <main class="flex-1 max-w-3xl mx-auto px-4 pt-24 pb-16 w-full">
      <div class="flex items-center gap-2 mb-2">
        <Percent class="h-5 w-5 text-zinc-500" />
        <h1 class="text-2xl font-semibold text-zinc-900">Settings</h1>
      </div>
      <p class="text-sm text-zinc-500 mb-8">
        Manage the fleet-wide rental discount policy.
      </p>

      <div v-if="loading" class="text-center py-20">
        <p class="text-sm text-zinc-500">Loading...</p>
      </div>

      <template v-else>
        <div class="rounded-lg border border-zinc-200 bg-white p-6 space-y-6">
          <div class="flex items-center gap-2">
            <BadgeCheck class="h-4 w-4 text-green-600" />
            <span class="text-xs font-medium text-green-700 bg-green-50 border border-green-200 rounded-full px-2.5 py-1">
              Global default — applies to all vehicles
            </span>
          </div>

          <div class="space-y-2">
            <Label>Policy Name</Label>
            <Input v-model="name" />
          </div>

          <div class="space-y-2">
            <Label>Description</Label>
            <Input v-model="description" />
          </div>

          <div class="space-y-3">
            <div class="flex items-center justify-between">
              <Label>Discount Tiers (by rental days)</Label>
              <Button variant="outline" size="sm" @click="addTier">
                <Plus class="h-4 w-4 mr-1" /> Add Tier
              </Button>
            </div>

            <p class="text-xs text-zinc-400">
              The longest matching duration wins. The first tier must start at 1 day.
            </p>

            <div v-for="(tier, idx) in tiers" :key="idx" class="flex items-end gap-3">
              <div class="flex-1">
                <Label>Minimum days</Label>
                <Input v-model="tier.min_days" type="number" min="1" />
              </div>
              <div class="flex-1">
                <Label>Discount %</Label>
                <Input v-model="tier.discount_percent" type="number" min="0" max="100" step="0.01" />
              </div>
              <button
                type="button"
                class="h-10 w-10 flex items-center justify-center text-zinc-400 hover:text-red-600"
                @click="removeTier(idx)"
                :disabled="tiers.length <= 1"
              >
                <Trash2 class="h-4 w-4" />
              </button>
            </div>

            <p v-if="tiersLabel" class="text-xs text-zinc-500 bg-zinc-50 border border-zinc-100 rounded p-3">
              <span class="font-medium">Preview:</span> {{ tiersLabel }}
            </p>
          </div>

          <p v-if="error" class="text-sm text-red-600 flex items-start gap-1.5">
            <AlertCircle class="h-4 w-4 mt-0.5 shrink-0" /> {{ error }}
          </p>
          <p v-if="success" class="text-sm text-green-600">{{ success }}</p>

          <Button class="w-full" :disabled="saving" @click="savePolicy">
            <Save class="h-4 w-4 mr-1.5" />
            {{ saving ? 'Saving...' : 'Save Discount Policy' }}
          </Button>
        </div>
      </template>
    </main>
  </div>
</template>

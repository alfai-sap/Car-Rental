<script setup lang="ts">
import { ref } from 'vue'
import { RouterLink } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { Eye, EyeOff } from 'lucide-vue-next'
import Navbar from '@/components/Navbar.vue'
import Button from '@/components/ui/Button.vue'
import Input from '@/components/ui/Input.vue'
import Label from '@/components/ui/Label.vue'

const auth = useAuthStore()

const countryCodes = [
  { code: '+63', label: '🇵🇭 PH +63' },
  { code: '+1',  label: '🇺🇸 US +1' },
  { code: '+44', label: '🇬🇧 UK +44' },
  { code: '+81', label: '🇯🇵 JP +81' },
  { code: '+82', label: '🇰🇷 KR +82' },
  { code: '+86', label: '🇨🇳 CN +86' },
  { code: '+61', label: '🇦🇺 AU +61' },
  { code: '+65', label: '🇸🇬 SG +65' },
  { code: '+60', label: '🇲🇾 MY +60' },
  { code: '+66', label: '🇹🇭 TH +66' },
]

const firstName = ref('')
const lastName = ref('')
const email = ref('')
const countryCode = ref('+63')
const phone = ref('')
const password = ref('')
const password2 = ref('')
const showPassword = ref(false)
const error = ref('')
const loading = ref(false)
const registered = ref(false)

function formatPhone(value: string): string {
  return value.replace(/\D/g, '').slice(0, 10)
}

function onPhoneInput(event: Event) {
  const input = event.target as HTMLInputElement
  phone.value = formatPhone(input.value)
}

function validatePhone(number: string): boolean {
  // Must be exactly 10 digits
  return /^\d{10}$/.test(number)
}

async function handleRegister() {
  loading.value = true
  error.value = ''

  if (password.value !== password2.value) {
    error.value = 'Passwords do not match.'
    loading.value = false
    return
  }

  if (!phone.value || !validatePhone(phone.value)) {
    error.value = 'Phone number must be exactly 10 digits.'
    loading.value = false
    return
  }

  try {
    await auth.register({
      email: email.value,
      first_name: firstName.value,
      last_name: lastName.value,
      phone: countryCode.value + phone.value,
      password: password.value,
      password2: password2.value,
    })
    registered.value = true
  } catch (err: unknown) {
    const data = (err as { response?: { data?: Record<string, string[]> } })?.response?.data
    if (data) {
      const messages = Object.values(data).flat()
      error.value = messages.join('. ')
    } else {
      error.value = 'Registration failed. Please try again.'
    }
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="min-h-screen flex flex-col bg-zinc-50">
    <Navbar />

    <div class="flex-1 flex items-center justify-center px-4 pt-16">
      <div class="w-full max-w-sm">
        <h1 class="text-2xl font-semibold text-zinc-900 text-center mb-8 tracking-tight">
          Create Account
        </h1>

        <!-- Registration success -->
        <div v-if="registered" class="text-center space-y-4">
          <p class="text-sm text-green-600">Account created successfully.</p>
          <p class="text-sm text-zinc-500">
            Please check your email to verify your account before signing in.
          </p>
          <RouterLink to="/login" class="text-sm text-zinc-900 font-medium hover:underline">
            Go to Sign In
          </RouterLink>
        </div>

        <form v-else @submit.prevent="handleRegister" class="space-y-5">
          <div class="grid grid-cols-2 gap-4">
            <div class="space-y-2">
              <Label>First Name</Label>
              <Input v-model="firstName" type="text" required />
            </div>
            <div class="space-y-2">
              <Label>Last Name</Label>
              <Input v-model="lastName" type="text" required />
            </div>
          </div>

          <div class="space-y-2">
            <Label>Email</Label>
            <Input v-model="email" type="email" required />
          </div>

          <div class="space-y-2">
            <Label>Phone Number</Label>
            <div class="flex gap-2">
              <select
                v-model="countryCode"
                class="h-10 rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-zinc-400 focus:border-transparent"
              >
                <option v-for="c in countryCodes" :key="c.code" :value="c.code">{{ c.label }}</option>
              </select>
              <Input
                :model-value="phone"
                @input="onPhoneInput"
                type="text"
                inputmode="numeric"
                placeholder="912 345 6789"
                maxlength="10"
                required
                class="flex-1"
              />
            </div>
          </div>

          <div class="space-y-2">
            <Label>Password</Label>
            <div class="relative">
              <Input v-model="password" :type="showPassword ? 'text' : 'password'" required class="pr-10" />
              <button
                type="button"
                class="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-400 hover:text-zinc-600"
                @click="showPassword = !showPassword"
                tabindex="-1"
              >
                <EyeOff v-if="showPassword" class="h-4 w-4" />
                <Eye v-else class="h-4 w-4" />
              </button>
            </div>
          </div>

          <div class="space-y-2">
            <Label>Confirm Password</Label>
            <Input v-model="password2" :type="showPassword ? 'text' : 'password'" required class="pr-10" />
          </div>

          <p v-if="error" class="text-sm text-red-600">{{ error }}</p>

          <Button type="submit" class="w-full" :disabled="loading">
            {{ loading ? 'Creating...' : 'Create Account' }}
          </Button>
        </form>

        <p class="text-sm text-center text-zinc-500 mt-6">
          Already have an account?
          <RouterLink to="/login" class="text-zinc-900 font-medium hover:underline">
            Sign In
          </RouterLink>
        </p>
      </div>
    </div>
  </div>
</template>


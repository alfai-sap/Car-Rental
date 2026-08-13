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

const email = ref('')
const password = ref('')
const password2 = ref('')
const showPassword = ref(false)
const error = ref('')
const loading = ref(false)
const registered = ref(false)

async function handleRegister() {
  loading.value = true
  error.value = ''

  if (password.value !== password2.value) {
    error.value = 'Passwords do not match.'
    loading.value = false
    return
  }

  try {
    await auth.register({
      email: email.value,
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
          <div class="space-y-2">
            <Label>Email</Label>
            <Input v-model="email" type="email" required />
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

        <p v-if="!registered" class="text-sm text-center text-zinc-500 mt-6">
          Already have an account?
          <RouterLink to="/login" class="text-zinc-900 font-medium hover:underline">
            Sign In
          </RouterLink>
        </p>
      </div>
    </div>
  </div>
</template>


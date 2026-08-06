<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useRouter, RouterLink } from 'vue-router'
import { Eye, EyeOff, Shield } from 'lucide-vue-next'
import Button from '@/components/ui/Button.vue'
import Input from '@/components/ui/Input.vue'
import Label from '@/components/ui/Label.vue'

const auth = useAuthStore()
const router = useRouter()

const email = ref('')
const password = ref('')
const showPassword = ref(false)
const error = ref('')
const loading = ref(false)

onMounted(() => {
  if (auth.isAuthenticated && auth.user?.is_staff) {
    router.push('/admin/dashboard')
  }
})

async function handleLogin() {
  loading.value = true
  error.value = ''
  try {
    await auth.login(email.value, password.value)
    if (!auth.user?.is_staff) {
      error.value = 'This account does not have administrator privileges.'
      auth.logout()
      return
    }
    router.push('/admin/dashboard')
  } catch {
    error.value = 'Invalid email or password.'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="min-h-screen flex flex-col bg-zinc-50">
    <header class="fixed top-0 left-0 right-0 z-50 bg-white/80 backdrop-blur-sm border-b border-zinc-200">
      <nav class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="flex items-center justify-between h-16">
          <RouterLink to="/" class="text-lg font-semibold text-zinc-900 tracking-tight">
            Car Rental
          </RouterLink>
        </div>
      </nav>
    </header>

    <div class="flex-1 flex items-center justify-center px-4 pt-16">
      <div class="w-full max-w-sm">
        <div class="text-center mb-8">
          <div class="inline-flex items-center justify-center h-12 w-12 rounded-full bg-zinc-900 mb-4">
            <Shield class="h-6 w-6 text-white" />
          </div>
          <h1 class="text-2xl font-semibold text-zinc-900 tracking-tight">
            Admin Login
          </h1>
          <p class="text-sm text-zinc-500 mt-1">Sign in to access the admin dashboard.</p>
        </div>

        <form @submit.prevent="handleLogin" class="space-y-5">
          <div class="space-y-2">
            <Label>Email</Label>
            <Input v-model="email" type="email" required />
          </div>

          <div class="space-y-2">
            <Label>Password</Label>
            <div class="relative">
              <Input v-model="password" :type="showPassword ? 'text' : 'password'" required />
              <button
                type="button"
                class="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-400 hover:text-zinc-600"
                @click="showPassword = !showPassword"
              >
                <EyeOff v-if="showPassword" class="h-4 w-4" />
                <Eye v-else class="h-4 w-4" />
              </button>
            </div>
          </div>

          <p v-if="error" class="text-sm text-red-600">{{ error }}</p>

          <Button class="w-full" :disabled="loading" type="submit">
            {{ loading ? 'Signing In...' : 'Sign In' }}
          </Button>
        </form>
      </div>
    </div>
  </div>
</template>

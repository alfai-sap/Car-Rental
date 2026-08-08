<script setup lang="ts">
import { ref } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useRouter, useRoute, RouterLink } from 'vue-router'
import { Eye, EyeOff } from 'lucide-vue-next'
import Navbar from '@/components/Navbar.vue'
import Button from '@/components/ui/Button.vue'
import Input from '@/components/ui/Input.vue'
import Label from '@/components/ui/Label.vue'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()

const email = ref('')
const password = ref('')
const showPassword = ref(false)
const error = ref('')
const loading = ref(false)

async function handleLogin() {
  loading.value = true
  error.value = ''
  try {
    await auth.login(email.value, password.value)
    const redirect = (route.query.redirect as string) || '/'
    router.push(redirect)
  } catch (err: unknown) {
    const response = (err as { response?: { data?: { detail?: string; email?: string[]; password?: string[] } } })?.response
    const data = response?.data
    if (data?.detail) {
      error.value = data.detail
    } else if (data) {
      const messages = Object.values(data).flat().filter(Boolean)
      error.value = messages.join('. ') || 'Invalid email or password.'
    } else {
      error.value = 'Invalid email or password.'
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
          Sign In
        </h1>

        <form @submit.prevent="handleLogin" class="space-y-5">
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

          <p v-if="error" class="text-sm text-red-600">{{ error }}</p>

          <Button type="submit" class="w-full" :disabled="loading">
            {{ loading ? 'Signing in...' : 'Sign In' }}
          </Button>

          <p class="text-sm text-center">
            <RouterLink to="/forgot-password" class="text-zinc-500 hover:text-zinc-900 hover:underline">
              Forgot your password?
            </RouterLink>
          </p>
        </form>

        <p class="text-sm text-center text-zinc-500 mt-6">
          Don't have an account?
          <RouterLink to="/register" class="text-zinc-900 font-medium hover:underline">
            Register
          </RouterLink>
        </p>
      </div>
    </div>
  </div>
</template>



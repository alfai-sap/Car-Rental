<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter, RouterLink } from 'vue-router'
import { Eye, EyeOff } from 'lucide-vue-next'
import Navbar from '@/components/Navbar.vue'
import Button from '@/components/ui/Button.vue'
import Input from '@/components/ui/Input.vue'
import Label from '@/components/ui/Label.vue'
import api from '@/services/api'

const route = useRoute()
const router = useRouter()

const uid = route.params.uid as string
const token = route.params.token as string

const password = ref('')
const password2 = ref('')
const showPassword = ref(false)
const loading = ref(false)
const success = ref(false)
const error = ref('')

async function handleSubmit() {
  loading.value = true
  error.value = ''

  if (password.value !== password2.value) {
    error.value = 'Passwords do not match.'
    loading.value = false
    return
  }

  try {
    await api.post('/auth/reset-password/confirm/', {
      uid: uid,
      token: token,
      password: password.value,
      password2: password2.value,
    })
    success.value = true
    // Redirect to login after 3 seconds
    setTimeout(() => {
      router.push('/login')
    }, 3000)
  } catch (err: unknown) {
    const data = (err as { response?: { data?: { detail?: string } } })?.response?.data
    error.value = data?.detail || 'Reset link has expired or is invalid.'
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
        <h1 class="text-2xl font-semibold text-zinc-900 text-center mb-2 tracking-tight">
          New Password
        </h1>
        <p class="text-sm text-zinc-500 text-center mb-8">
          Enter your new password below.
        </p>

        <div v-if="success" class="text-center">
          <p class="text-sm text-green-600 mb-2">Password reset successful.</p>
          <p class="text-sm text-zinc-500">Redirecting you to sign in...</p>
        </div>

        <form v-else @submit.prevent="handleSubmit" class="space-y-5">
          <div class="space-y-2">
            <Label>New Password</Label>
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
            <Input v-model="password2" type="password" required />
          </div>

          <p v-if="error" class="text-sm text-red-600">{{ error }}</p>

          <Button type="submit" class="w-full" :disabled="loading">
            {{ loading ? 'Resetting...' : 'Reset Password' }}
          </Button>
        </form>
      </div>
    </div>
  </div>
</template>

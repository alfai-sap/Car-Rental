<script setup lang="ts">
import { ref } from 'vue'
import { RouterLink } from 'vue-router'
import Navbar from '@/components/Navbar.vue'
import Button from '@/components/ui/Button.vue'
import Input from '@/components/ui/Input.vue'
import Label from '@/components/ui/Label.vue'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()

const email = ref('')
const loading = ref(false)
const sent = ref(false)
const error = ref('')

async function handleSubmit() {
  loading.value = true
  error.value = ''
  sent.value = false
  try {
    await auth.resendVerification(email.value)
    sent.value = true
  } catch (err: unknown) {
    // The endpoint is anti-enumerating and returns 200 for any input.
    // Treat any failure as generic.
    const data = (err as { response?: { data?: { detail?: string } } })?.response?.data
    error.value = data?.detail || 'Something went wrong. Please try again.'
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
          Resend Verification Email
        </h1>
        <p class="text-sm text-zinc-500 text-center mb-8">
          Enter your email and we'll send you a new verification link.
        </p>

        <div v-if="sent" class="text-center">
          <p class="text-sm text-green-600 mb-4">
            If this email exists, a verification email will be sent.
          </p>
          <RouterLink to="/login" class="text-sm text-zinc-900 font-medium hover:underline">
            Return to Sign In
          </RouterLink>
        </div>

        <form v-else @submit.prevent="handleSubmit" class="space-y-5">
          <div class="space-y-2">
            <Label>Email</Label>
            <Input v-model="email" type="email" required />
          </div>

          <p v-if="error" class="text-sm text-red-600">{{ error }}</p>

          <Button type="submit" class="w-full" :disabled="loading">
            {{ loading ? 'Sending...' : 'Send Verification Email' }}
          </Button>

          <p class="text-sm text-center">
            <RouterLink to="/login" class="text-zinc-500 hover:text-zinc-900 hover:underline">
              Back to Sign In
            </RouterLink>
          </p>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, RouterLink } from 'vue-router'
import Navbar from '@/components/Navbar.vue'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const auth = useAuthStore()

const uid = route.params.uid as string
const token = route.params.token as string

const loading = ref(true)
const success = ref(false)
const error = ref('')

async function verify() {
  loading.value = true
  try {
    await auth.verifyEmail(uid, token)
    success.value = true
  } catch (err: unknown) {
    const data = (err as { response?: { data?: { detail?: string } } })?.response?.data
    error.value = data?.detail || 'Verification failed. The link may have expired.'
  } finally {
    loading.value = false
  }
}

verify()
</script>

<template>
  <div class="min-h-screen flex flex-col bg-zinc-50">
    <Navbar />
    <div class="flex-1 flex items-center justify-center px-4 pt-16">
      <div class="w-full max-w-sm text-center">
        <h1 class="text-2xl font-semibold text-zinc-900 mb-6 tracking-tight">
          Email Verification
        </h1>

        <p v-if="loading" class="text-sm text-zinc-500">Verifying your email...</p>

        <div v-else-if="success" class="space-y-4">
          <p class="text-sm text-green-600">Your email has been verified successfully.</p>
          <p class="text-sm text-zinc-500">You can now sign in to your account.</p>
          <RouterLink to="/login" class="inline-block text-sm text-zinc-900 font-medium hover:underline mt-2">
            Go to Sign In
          </RouterLink>
        </div>

        <div v-else-if="error" class="space-y-4">
          <p class="text-sm text-red-600">{{ error }}</p>
          <RouterLink to="/login" class="inline-block text-sm text-zinc-900 font-medium hover:underline">
            Back to Sign In
          </RouterLink>
        </div>
      </div>
    </div>
  </div>
</template>

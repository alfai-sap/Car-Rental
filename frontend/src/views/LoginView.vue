<script setup lang="ts">
import { ref } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useRouter, RouterLink } from 'vue-router'
import Navbar from '@/components/Navbar.vue'
import Button from '@/components/ui/Button.vue'
import Input from '@/components/ui/Input.vue'
import Label from '@/components/ui/Label.vue'

const auth = useAuthStore()
const router = useRouter()

const username = ref('')
const password = ref('')
const error = ref('')

async function handleLogin() {
  try {
    error.value = ''
    await auth.login(username.value, password.value)
    router.push('/')
  } catch {
    error.value = 'Invalid username or password'
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
            <Label>Username</Label>
            <Input v-model="username" type="text" required />
          </div>

          <div class="space-y-2">
            <Label>Password</Label>
            <Input v-model="password" type="password" required />
          </div>

          <p v-if="error" class="text-sm text-red-600">{{ error }}</p>

          <Button type="submit" class="w-full">Sign In</Button>
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


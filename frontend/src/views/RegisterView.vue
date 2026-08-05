<script setup lang="ts">
import { ref } from 'vue'
import { RouterLink } from 'vue-router'
import Navbar from '@/components/Navbar.vue'
import Button from '@/components/ui/Button.vue'
import Input from '@/components/ui/Input.vue'
import Label from '@/components/ui/Label.vue'

const username = ref('')
const email = ref('')
const password = ref('')
const password2 = ref('')
const error = ref('')
const success = ref('')

async function handleRegister() {
  error.value = ''
  success.value = ''

  if (password.value !== password2.value) {
    error.value = 'Passwords do not match'
    return
  }

  // Registration will be implemented in Phase 2 (Authentication)
  success.value = 'Registration will be available in the next phase.'
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

        <form @submit.prevent="handleRegister" class="space-y-5">
          <div class="space-y-2">
            <Label>Username</Label>
            <Input v-model="username" type="text" required />
          </div>

          <div class="space-y-2">
            <Label>Email</Label>
            <Input v-model="email" type="email" required />
          </div>

          <div class="space-y-2">
            <Label>Password</Label>
            <Input v-model="password" type="password" required />
          </div>

          <div class="space-y-2">
            <Label>Confirm Password</Label>
            <Input v-model="password2" type="password" required />
          </div>

          <p v-if="error" class="text-sm text-red-600">{{ error }}</p>
          <p v-if="success" class="text-sm text-green-600">{{ success }}</p>

          <Button type="submit" class="w-full">Create Account</Button>
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

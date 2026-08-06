<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { User } from 'lucide-vue-next'
import Button from '@/components/ui/Button.vue'

const auth = useAuthStore()
const dropdownOpen = ref(false)

function toggleDropdown() {
  dropdownOpen.value = !dropdownOpen.value
}

function closeDropdown() {
  dropdownOpen.value = false
}

onMounted(async () => {
  const token = localStorage.getItem('access_token')
  if (token && !auth.user) {
    await auth.fetchUser()
  }
})
</script>

<template>
  <header class="fixed top-0 left-0 right-0 z-50 bg-white/80 backdrop-blur-sm border-b border-zinc-200">
    <nav class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <div class="flex items-center justify-between h-16">
        <RouterLink
          to="/"
          class="text-lg font-semibold text-zinc-900 tracking-tight"
        >
          Car Rental
        </RouterLink>

        <div class="flex-1" />

        <!-- Authenticated state -->
        <div v-if="auth.isAuthenticated && auth.user" class="relative">
          <button
            @click="toggleDropdown"
            class="flex items-center gap-2 rounded-full hover:ring-2 hover:ring-zinc-200 focus:outline-none transition"
          >
            <div class="h-9 w-9 rounded-full bg-zinc-800 flex items-center justify-center">
              <User class="h-4 w-4 text-white" />
            </div>
          </button>

          <!-- Dropdown -->
          <div
            v-if="dropdownOpen"
            class="absolute right-0 mt-2 w-56 rounded-md border border-zinc-200 bg-white shadow-lg z-50"
            @mouseleave="closeDropdown"
          >
            <div class="px-4 py-3 border-b border-zinc-100">
              <p class="text-sm font-medium text-zinc-900 truncate">
                {{ auth.user.first_name }} {{ auth.user.last_name }}
              </p>
              <p class="text-xs text-zinc-500 truncate">{{ auth.user.email }}</p>
            </div>
            <div class="p-1">
              <template v-if="auth.user?.is_staff">
                <RouterLink
                  to="/admin/dashboard"
                  class="block w-full text-left px-3 py-2 text-sm text-zinc-700 hover:bg-zinc-100 rounded"
                  @click="closeDropdown"
                >
                  Admin
                </RouterLink>
                <button
                  @click="auth.logout(); closeDropdown()"
                  class="w-full text-left px-3 py-2 text-sm text-zinc-700 hover:bg-zinc-100 rounded"
                >
                  Sign Out
                </button>
              </template>
              <template v-else>
                <RouterLink
                  to="/dashboard"
                  class="block w-full text-left px-3 py-2 text-sm text-zinc-700 hover:bg-zinc-100 rounded"
                  @click="closeDropdown"
                >
                  Dashboard
                </RouterLink>
                <RouterLink
                  to="/profile"
                  class="block w-full text-left px-3 py-2 text-sm text-zinc-700 hover:bg-zinc-100 rounded"
                  @click="closeDropdown"
                >
                  Profile
                </RouterLink>
                <button
                  @click="auth.logout(); closeDropdown()"
                  class="w-full text-left px-3 py-2 text-sm text-zinc-700 hover:bg-zinc-100 rounded"
                >
                  Sign Out
                </button>
              </template>
            </div>
          </div>
        </div>

        <!-- Unauthenticated state -->
        <div v-else class="flex items-center gap-2">
          <RouterLink to="/login">
            <Button variant="ghost" size="sm">Login</Button>
          </RouterLink>
          <RouterLink to="/register">
            <Button variant="ghost" size="sm">Register</Button>
          </RouterLink>
        </div>
      </div>
    </nav>
  </header>
</template>

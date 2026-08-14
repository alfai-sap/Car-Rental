<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { User } from 'lucide-vue-next'
import Button from '@/components/ui/Button.vue'

const auth = useAuthStore()
const router = useRouter()
const dropdownOpen = ref(false)

function toggleDropdown() {
  dropdownOpen.value = !dropdownOpen.value
}

function closeDropdown() {
  dropdownOpen.value = false
}

async function handleLogout() {
  await auth.logout()
  closeDropdown()
  router.push({ name: 'home' })
}

onMounted(async () => {
  if (!auth.user) {
    await auth.fetchUser()
  }
  await auth.fetchUnreadCount()
  setInterval(() => auth.fetchUnreadCount(), 60000)
})
</script>

<template>
  <header class="fixed top-0 left-0 right-0 z-50 bg-white/80 backdrop-blur-sm border-b border-zinc-200">
    <nav class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-4">
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
            class="flex items-center gap-2 rounded-full hover:ring-2 hover:ring-zinc-200 focus:outline-none transition relative"
          >
            <div class="h-9 w-9 rounded-full bg-zinc-800 flex items-center justify-center">
              <User class="h-4 w-4 text-white" />
            </div>
            <!-- Unread notification badge -->
            <span
              v-if="auth.unreadNotificationCount > 0"
              class="absolute -top-1 -right-1 h-5 w-5 rounded-full bg-red-500 text-white text-[10px] font-bold flex items-center justify-center"
            >
              {{ auth.unreadNotificationCount > 99 ? '99+' : auth.unreadNotificationCount }}
            </span>
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
                  Dashboard
                </RouterLink>
                <RouterLink
                  to="/admin/vehicles"
                  class="block w-full text-left px-3 py-2 text-sm text-zinc-700 hover:bg-zinc-100 rounded"
                  @click="closeDropdown"
                >
                  Manage Vehicles
                </RouterLink>
                <RouterLink
                  to="/admin/audit-logs"
                  class="block w-full text-left px-3 py-2 text-sm text-zinc-700 hover:bg-zinc-100 rounded"
                  @click="closeDropdown"
                >
                  Audit Log
                </RouterLink>
                <RouterLink
                  to="/admin/settings"
                  class="block w-full text-left px-3 py-2 text-sm text-zinc-700 hover:bg-zinc-100 rounded"
                  @click="closeDropdown"
                >
                  Settings
                </RouterLink>
                <RouterLink
                  to="/notifications"
                  class="flex items-center justify-between w-full text-left px-3 py-2 text-sm text-zinc-700 hover:bg-zinc-100 rounded"
                  @click="closeDropdown"
                >
                  <span>Notifications</span>
                  <span v-if="auth.unreadNotificationCount > 0" class="bg-red-500 text-white text-[10px] font-bold rounded-full h-4 w-4 flex items-center justify-center">
                    {{ auth.unreadNotificationCount > 99 ? '99+' : auth.unreadNotificationCount }}
                  </span>
                </RouterLink>
                <button
                  @click="handleLogout()"
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
                  to="/notifications"
                  class="flex items-center justify-between w-full text-left px-3 py-2 text-sm text-zinc-700 hover:bg-zinc-100 rounded"
                  @click="closeDropdown"
                >
                  <span>Notifications</span>
                  <span v-if="auth.unreadNotificationCount > 0" class="bg-red-500 text-white text-[10px] font-bold rounded-full h-4 w-4 flex items-center justify-center">
                    {{ auth.unreadNotificationCount > 99 ? '99+' : auth.unreadNotificationCount }}
                  </span>
                </RouterLink>
                <RouterLink
                  to="/profile"
                  class="block w-full text-left px-3 py-2 text-sm text-zinc-700 hover:bg-zinc-100 rounded"
                  @click="closeDropdown"
                >
                  Profile
                </RouterLink>
                <button
                  @click="handleLogout()"
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

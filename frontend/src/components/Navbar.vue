<script setup lang="ts">
import { RouterLink } from 'vue-router'
import Button from '@/components/ui/Button.vue'
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

        <div class="flex items-center gap-2">
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

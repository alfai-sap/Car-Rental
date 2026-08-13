<script setup lang="ts">
import Navbar from '@/components/Navbar.vue'
import { RouterLink } from 'vue-router'
import Button from '@/components/ui/Button.vue'
import { Car } from 'lucide-vue-next'
</script>

<template>
  <div class="min-h-screen flex flex-col">
    <Navbar />

    <!-- Hero Section -->
    <section class="flex-1 flex items-center justify-center px-4 pt-16">
      <div class="max-w-3xl mx-auto text-center">
        <!-- <div class="inline-flex items-center justify-center w-16 h-16 rounded-full bg-zinc-100 mb-8">
          <Car class="w-8 h-8 text-zinc-600" />
        </div> -->
        <h1 class="text-4xl sm:text-5xl lg:text-6xl font-semibold text-zinc-900 tracking-tight leading-tight">
          FIND YOUR PERFECT RIDE
        </h1>
        <p class="mt-6 text-lg text-zinc-500 max-w-xl mx-auto leading-relaxed">
          Browse our fleet of quality vehicles and book your next journey.
          Simple, fast, and reliable car rental at your fingertips.
        </p>
        <div class="mt-10 flex items-center justify-center gap-4">
          <RouterLink to="/vehicles">
            <Button size="lg">Browse Vehicles</Button>
          </RouterLink>
        </div>
      </div>
    </section>

    <!-- Footer -->
    <footer class="py-8 text-center text-sm text-zinc-400">
      <p>&copy; {{ new Date().getFullYear() }} Car Rental. All rights reserved.</p>
    </footer>
  </div>
</template>


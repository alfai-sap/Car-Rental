<script setup lang="ts">
import Navbar from '@/components/Navbar.vue'
import { RouterLink } from 'vue-router'
import Button from '@/components/ui/Button.vue'
import { Car } from 'lucide-vue-next'
import heroimage from '@/assets/car2.webp'
</script>

<template>
  <div class="min-h-screen flex flex-col">
    <Navbar />


    <!-- Hero Section -->
    <section class="relative flex-1 flex items-center justify-center px-4 pt-16 bg-cover bg-center"
      :style="{ backgroundImage: `url(${heroimage})` }">

      <div class="absolute inset-0 bg-black/60"></div> 

      <div class="relative max-w-3xl mx-auto text-center">

        <h1 class="text-4xl sm:text-5xl lg:text-6xl font-semibold text-white tracking-tight leading-tight">
          FIND YOUR PERFECT RIDE
        </h1>

        <p class="mt-6 text-lg text-white/80 max-w-xl mx-auto leading-relaxed">
          Browse our fleet of quality vehicles and book your next journey.
          <!-- Simple, fast, and reliable car rental at your fingertips. -->
        </p>
        <div class="mt-10 flex items-center justify-center gap-4">
          <RouterLink to="/vehicles">
            <Button class="bg-white! text-black! hover:bg-zinc-800! hover:text-white!" size="lg">Browse Vehicles</Button>
          </RouterLink>
        </div>
      </div>

    </section>

    <!-- Footer -->
    <footer class="py-2 text-center text-sm text-zinc-900">
      <p>&copy; {{ new Date().getFullYear() }} Car Rental. All rights reserved.</p>
    </footer>
  </div>
</template>


<template>
  <div class="flex min-h-screen items-center justify-center bg-gray-100">
    <div class="text-center">
      <h1 class="text-3xl font-bold text-gray-800">About Us</h1>
      <p class="mt-2 text-gray-600">{{ title || 'Car Rental Management System' }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{ title?: string }>()
</script>

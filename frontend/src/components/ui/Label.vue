<script setup lang="ts">
import { cn } from '@/lib/utils'
import { useId } from 'vue'

const id = useId()
</script>

<template>
  <label
    :for="id"
    :class="cn(
      'text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70',
    )"
  >
    <slot />
  </label>
</template>

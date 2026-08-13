<script setup lang="ts">
import { cn } from '@/lib/utils'

defineProps<{
  modelValue?: string
  type?: string
  placeholder?: string
  disabled?: boolean
  required?: boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [value: string]
}>()
</script>

<template>
  <input
    v-bind="$attrs"
    :value="modelValue"
    @input="emit('update:modelValue', ($event.target as HTMLInputElement).value)"
    :class="cn(
      'flex h-10 w-full rounded-md border border-zinc-300 bg-surface px-3 py-2 text-sm placeholder:text-zinc-400 focus:outline-none focus:ring-2 focus:ring-zinc-400 focus:border-transparent disabled:cursor-not-allowed disabled:opacity-50',
    )"
  />
</template>

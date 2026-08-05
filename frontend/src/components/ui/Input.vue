<script setup lang="ts">
import { cn } from '@/lib/utils'
import { useId, type InputHTMLAttributes } from 'vue'

interface InputProps extends /* @vue-ignore */ InputHTMLAttributes {
  modelValue?: string
}

const props = defineProps<InputProps>()
const emit = defineEmits<{
  'update:modelValue': [value: string]
}>()

const id = useId()
</script>

<template>
  <input
    :id="id"
    :value="modelValue"
    @input="emit('update:modelValue', ($event.target as HTMLInputElement).value)"
    :class="cn(
      'flex h-10 w-full rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm placeholder:text-zinc-400 focus:outline-none focus:ring-2 focus:ring-zinc-400 focus:border-transparent disabled:cursor-not-allowed disabled:opacity-50',
    )"
  />
</template>

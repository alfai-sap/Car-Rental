<script setup lang="ts">
import { cn } from '@/lib/utils'

defineProps<{
  variant?: 'default' | 'ghost' | 'outline'
  size?: 'default' | 'sm' | 'lg'
}>()
</script>

<template>
  <component
    :is="'button'"
    v-bind="$attrs"
    :class="cn(
      'inline-flex items-center justify-center font-medium rounded-md transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50',
      {
        'bg-zinc-900 text-white hover:bg-zinc-800': (variant ?? 'default') === 'default',
        'text-zinc-700 hover:bg-zinc-100 border-0 bg-transparent': variant === 'ghost',
        'border border-zinc-300 bg-transparent text-zinc-700 hover:bg-zinc-100': variant === 'outline',
      },
      {
        'h-10 px-4 py-2 text-sm': (size ?? 'default') === 'default',
        'h-9 px-3 text-sm': size === 'sm',
        'h-11 px-8 text-base': size === 'lg',
      },
    )"
  >
    <slot />
  </component>
</template>

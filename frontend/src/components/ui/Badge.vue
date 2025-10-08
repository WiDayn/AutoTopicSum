<template>
  <div
    :class="cn(badgeVariants({ variant }), $attrs.class)"
    v-bind="$attrs"
  >
    <slot />
  </div>
</template>

<script setup>
import { cva } from 'class-variance-authority'
import { cn } from '@/lib/utils'

defineProps({
  variant: {
    type: String,
    default: 'default'
  }
})

const badgeVariants = cva(
  'inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2',
  {
    variants: {
      variant: {
        default: 'border-transparent bg-primary text-primary-foreground hover:bg-primary/80',
        secondary: 'border-transparent bg-secondary text-secondary-foreground hover:bg-secondary/80',
        outline: 'text-foreground',
      },
    },
  }
)
</script>


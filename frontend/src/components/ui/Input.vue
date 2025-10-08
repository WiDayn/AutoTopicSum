<template>
  <input
    :class="cn(
      'flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50',
      $attrs.class
    )"
    :value="modelValue"
    @input="$emit('update:modelValue', $event.target.value)"
    v-bind="omitAttrs"
  />
</template>

<script setup>
import { computed, useAttrs } from 'vue'
import { cn } from '@/lib/utils'

const props = defineProps({
  modelValue: {
    type: [String, Number],
    default: ''
  }
})

const emit = defineEmits(['update:modelValue'])

// 从 $attrs 中排除 class，因为已经在模板中处理了
const omitAttrs = computed(() => {
  const { class: _, ...rest } = useAttrs()
  return rest
})
</script>


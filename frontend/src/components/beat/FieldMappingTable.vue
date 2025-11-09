<template>
  <div class="space-y-4">
    <div class="flex items-center justify-between">
      <h4 class="text-lg font-semibold">编码映射</h4>
      <Button
        v-if="entries.length > previewCount"
        variant="ghost"
        size="sm"
        @click="toggle"
      >
        {{ showAll ? '收起' : '展开全部' }}
      </Button>
    </div>
    <div class="rounded-lg border">
      <table class="min-w-full divide-y text-sm">
        <thead class="bg-muted/50">
          <tr>
            <th class="px-4 py-3 text-left font-semibold">原始关键词</th>
            <th class="px-4 py-3 text-left font-semibold">→</th>
            <th class="px-4 py-3 text-left font-semibold">编码后关键词</th>
          </tr>
        </thead>
        <tbody class="divide-y">
          <tr
            v-for="[original, encoded] in displayEntries"
            :key="original"
            class="hover:bg-muted/30"
          >
            <td class="px-4 py-3">{{ original }}</td>
            <td class="px-4 py-3 text-center text-muted-foreground">→</td>
            <td class="px-4 py-3">
              <Badge variant="default">{{ encoded }}</Badge>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'

const props = defineProps({
  mapping: {
    type: Object,
    default: () => ({})
  },
  previewCount: {
    type: Number,
    default: 10
  },
  resetKey: {
    type: [String, Number],
    default: ''
  }
})

const showAll = ref(false)

const entries = computed(() => {
  const rawEntries = Object.entries(props.mapping || {})
  return rawEntries.sort(([a], [b]) => a.localeCompare(b, 'zh-CN'))
})

const displayEntries = computed(() => {
  if (showAll.value) {
    return entries.value
  }
  return entries.value.slice(0, props.previewCount)
})

const toggle = () => {
  showAll.value = !showAll.value
}

watch(
  () => props.resetKey,
  () => {
    showAll.value = false
  },
  { immediate: true }
)
</script>


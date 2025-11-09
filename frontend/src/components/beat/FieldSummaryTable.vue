<template>
  <Card class="p-0 overflow-hidden">
    <div class="flex items-center justify-between border-b px-6 py-4">
      <div>
        <h3 class="text-lg font-semibold">字段压缩概览</h3>
        <p class="text-sm text-muted-foreground">
          点击行可查看对应字段的详细聚类情况
        </p>
      </div>
      <Badge variant="secondary">
        总压缩率 {{ overallReductionLabel }}
      </Badge>
    </div>

    <div class="overflow-x-auto">
      <table class="min-w-full divide-y">
        <thead class="bg-muted/40 text-xs uppercase tracking-wide text-muted-foreground">
          <tr>
            <th class="py-3 pl-6 pr-4 text-left font-medium">字段</th>
            <th class="px-4 py-3 text-left font-medium">原始</th>
            <th class="px-4 py-3 text-left font-medium">编码后</th>
            <th class="px-4 py-3 text-left font-medium">减少</th>
            <th class="px-4 py-3 text-left font-medium">减少率</th>
            <th class="px-4 py-3 text-left font-medium">聚类数</th>
            <th class="px-4 py-3 text-left font-medium">聚类覆盖</th>
          </tr>
        </thead>
        <tbody class="divide-y text-sm">
          <tr
            v-for="field in fields"
            :key="field.name"
            :class="[
              'cursor-pointer transition-colors hover:bg-muted/40',
              field.name === selectedField ? 'bg-primary/10 hover:bg-primary/15' : ''
            ]"
            @click="handleSelect(field.name)"
          >
            <td class="py-3 pl-6 pr-4 font-medium capitalize">
              {{ field.label }}
            </td>
            <td class="px-4 py-3">{{ field.before }}</td>
            <td class="px-4 py-3">{{ field.after }}</td>
            <td class="px-4 py-3 font-semibold text-green-600">
              {{ field.reduction }}
            </td>
            <td class="px-4 py-3">
              <div class="flex items-center gap-2">
                <div class="w-24 rounded-full bg-muted/40">
                  <div
                    class="h-2 rounded-full bg-primary transition-all"
                    :style="{ width: field.reductionRateBar }"
                  ></div>
                </div>
                <span class="font-medium">
                  {{ field.reductionRateLabel }}
                </span>
              </div>
            </td>
            <td class="px-4 py-3">
              <span class="font-medium">{{ field.clusterCount }}</span>
            </td>
            <td class="px-4 py-3">
              <span>{{ field.clusterCoverageLabel }}</span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </Card>
</template>

<script setup>
import { computed } from 'vue'
import Card from '@/components/ui/Card.vue'
import Badge from '@/components/ui/Badge.vue'

const props = defineProps({
  fields: {
    type: Array,
    default: () => []
  },
  selectedField: {
    type: String,
    default: ''
  },
  overallReduction: {
    type: Number,
    default: 0
  }
})

const emit = defineEmits(['select'])

const overallReductionLabel = computed(() => {
  if (!props.overallReduction || Number.isNaN(props.overallReduction)) {
    return '0%'
  }
  return `${props.overallReduction.toFixed(1)}%`
})

const handleSelect = (fieldName) => {
  emit('select', fieldName)
}
</script>


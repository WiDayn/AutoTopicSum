<template>
  <Card class="p-6">
    <div class="flex items-center justify-between mb-6">
      <div>
        <h2 class="text-xl font-semibold">聚类总体概览</h2>
        <p class="text-sm text-muted-foreground">
          最新更新时间：{{ stats.formattedTimestamp || '—' }}
        </p>
      </div>
      <Badge variant="outline">
        共 {{ stats.fieldCount }} 个字段
      </Badge>
    </div>

    <div class="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
      <div
        v-for="item in summaryItems"
        :key="item.label"
        class="rounded-lg border bg-muted/30 p-4"
      >
        <div class="text-sm text-muted-foreground">{{ item.label }}</div>
        <div class="mt-2 text-2xl font-semibold">
          {{ item.value }}
          <span
            v-if="item.suffix"
            class="ml-1 text-sm font-normal text-muted-foreground"
          >
            {{ item.suffix }}
          </span>
        </div>
        <p v-if="item.description" class="mt-2 text-xs text-muted-foreground">
          {{ item.description }}
        </p>
      </div>
    </div>
  </Card>
</template>

<script setup>
import { computed } from 'vue'
import Card from '@/components/ui/Card.vue'
import Badge from '@/components/ui/Badge.vue'

const props = defineProps({
  stats: {
    type: Object,
    default: () => ({})
  }
})

const summaryItems = computed(() => [
  {
    label: '原始关键词总量',
    value: props.stats.totalBefore ?? 0,
    description: '参与聚类前的唯一关键词数量'
  },
  {
    label: '编码后关键词总量',
    value: props.stats.totalAfter ?? 0,
    description: '聚类代表词（编码后）数量'
  },
  {
    label: '关键词减少量',
    value: props.stats.totalReduction ?? 0,
    suffix: '个',
    description: '聚类后压缩掉的关键词数'
  },
  {
    label: '整体减少率',
    value: props.stats.reductionRateLabel ?? '0%',
    description: '整体压缩效率（越高越好）'
  },
  {
    label: '形成聚类数量',
    value: props.stats.totalClusters ?? 0,
    suffix: '组',
    description: '拥有多个成员的聚类数量'
  },
  {
    label: '进入聚类的关键词数',
    value: props.stats.clusteredKeywords ?? 0,
    suffix: '个',
    description: '被聚类归并的原始关键词数量'
  }
])
</script>


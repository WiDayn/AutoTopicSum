<template>
  <Card class="flex h-full flex-col">
    <div v-if="fieldStats" class="flex flex-1 flex-col gap-6 p-6">
      <div class="flex flex-col gap-2 border-b pb-4">
        <div class="flex items-center justify-between">
          <h3 class="text-xl font-semibold capitalize">
            {{ displayName }}
          </h3>
          <Badge variant="outline">
            聚类 {{ fieldStats.total_clusters ?? 0 }} 组
          </Badge>
        </div>
        <div class="flex flex-wrap gap-3 text-sm text-muted-foreground">
          <span>原始 {{ fieldStats.before_count ?? 0 }}</span>
          <span>编码后 {{ fieldStats.after_count ?? 0 }}</span>
          <span class="text-green-600">
            减少 {{ fieldStats.reduction ?? 0 }}（{{ formattedReductionRate }}）
          </span>
          <span>
            聚类覆盖 {{ clusterCoverageLabel }}
          </span>
        </div>
      </div>

      <section class="space-y-3">
        <div class="flex items-center justify-between">
          <h4 class="text-lg font-semibold">关键词压缩效果</h4>
        </div>
        <FieldBarChart :stats="fieldStats" />
      </section>

      <section v-if="hasSimilarityData" class="space-y-3">
        <div class="flex items-center justify-between">
          <h4 class="text-lg font-semibold">关键词相似图</h4>
          <span class="text-xs text-muted-foreground">
            显示相似度 ≥ {{ similarityThreshold * 100 }}%
          </span>
        </div>
        <FieldSimilarityGraph
          :matrix="fieldStats.similarity_matrix"
          :threshold="similarityThreshold"
        />
      </section>

      <section class="space-y-4">
        <h4 class="text-lg font-semibold">聚类详情</h4>
        <div
          v-if="(fieldStats?.clusters?.length || 0) > 0"
          class="grid gap-4 md:grid-cols-2"
        >
          <div
            v-for="cluster in fieldStats.clusters"
            :key="cluster.representative"
            class="rounded-lg border p-4 shadow-sm"
          >
            <div class="flex items-center justify-between">
              <Badge variant="default" class="font-semibold">
                {{ cluster.representative }}
              </Badge>
              <span class="text-xs text-muted-foreground">
                {{ cluster.size ?? cluster.members?.length ?? 0 }} 个成员
              </span>
            </div>
            <p
              v-if="(cluster.members?.length || 0) > 1"
              class="mt-2 text-xs text-muted-foreground"
            >
              合并 {{ (cluster.members?.length || 1) - 1 }} 个同义关键词
            </p>
            <div class="mt-3 flex flex-wrap gap-2">
              <Badge
                v-for="member in cluster.members"
                :key="member"
                variant="outline"
                class="text-xs"
                :class="{
                  'bg-primary/10 border-primary text-primary':
                    member === cluster.representative
                }"
              >
                {{ member }}
              </Badge>
            </div>
          </div>
        </div>
        <div v-else class="rounded-lg border bg-muted/40 p-4 text-sm text-muted-foreground">
          该字段暂无多成员聚类，所有关键词均保持唯一。
        </div>
      </section>

      <section v-if="hasMappings">
        <FieldMappingTable
          :mapping="mapping"
          :preview-count="mappingPreviewCount"
          :reset-key="fieldName"
        />
      </section>
    </div>

    <div v-else class="flex flex-1 items-center justify-center p-10 text-muted-foreground">
      请选择左侧字段查看详细信息
    </div>
  </Card>
</template>

<script setup>
import { computed } from 'vue'
import Card from '@/components/ui/Card.vue'
import Badge from '@/components/ui/Badge.vue'
import FieldBarChart from '@/components/beat/FieldBarChart.vue'
import FieldSimilarityGraph from '@/components/beat/FieldSimilarityGraph.vue'
import FieldMappingTable from '@/components/beat/FieldMappingTable.vue'

const props = defineProps({
  fieldName: {
    type: String,
    default: ''
  },
  fieldStats: {
    type: Object,
    default: null
  },
  mapping: {
    type: Object,
    default: () => ({})
  }
})

const similarityThreshold = 0.5
const mappingPreviewCount = 10

const displayName = computed(() =>
  props.fieldName ? props.fieldName.replace(/_/g, ' ') : ''
)

const formattedReductionRate = computed(() => {
  const rate = props.fieldStats?.reduction_rate ?? 0
  return `${rate.toFixed(1)}%`
})

const clusterCoverageLabel = computed(() => {
  const before = props.fieldStats?.before_count ?? 0
  const clustered = props.fieldStats?.clustered_keywords ?? 0
  if (!before) return '0%'
  return `${((clustered / before) * 100).toFixed(1)}%`
})

const hasSimilarityData = computed(() => {
  const matrix = props.fieldStats?.similarity_matrix
  return Boolean(
    matrix &&
      Array.isArray(matrix.keywords) &&
      matrix.keywords.length > 1 &&
      Array.isArray(matrix.matrix)
  )
})

const hasMappings = computed(() => Object.keys(props.mapping || {}).length > 0)
</script>


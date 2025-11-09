<template>
  <div class="min-h-screen bg-background">
    <header class="border-b bg-card">
      <div class="container mx-auto px-4 py-4">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-4">
            <Button variant="ghost" @click="goBack">
              <ArrowLeft class="mr-2 h-4 w-4" />
              返回
            </Button>
            <h1 class="text-2xl font-bold">BEAT 编码器媒体分类聚类效果</h1>
          </div>
          <Badge v-if="recordData" variant="outline">
            相似度阈值：{{ recordData.similarity_threshold ?? '—' }}
          </Badge>
        </div>
      </div>
    </header>

    <main class="container mx-auto px-4 py-8">
      <div v-if="loading" class="flex items-center justify-center py-12">
        <div class="text-muted-foreground">加载中...</div>
      </div>

      <div v-else-if="error" class="flex items-center justify-center py-12">
        <Card class="max-w-md p-6 text-center text-destructive">
          {{ error }}
        </Card>
      </div>

      <div v-else-if="hasClusteringData" class="space-y-6">
        <ClusteringSummary :stats="summaryStats" />

        <div class="grid gap-6 lg:grid-cols-[2fr,3fr]">
          <FieldSummaryTable
            :fields="fieldList"
            :selected-field="activeField"
            :overall-reduction="overallReductionRate"
            @select="handleFieldSelect"
          />
          <FieldDetailPanel
            :field-name="activeField"
            :field-stats="activeFieldStats"
            :mapping="activeFieldMapping"
          />
        </div>
      </div>

      <div v-else class="flex items-center justify-center py-16">
        <Card class="max-w-lg p-8 text-center">
          <h2 class="text-xl font-semibold">暂无编码统计</h2>
          <p class="mt-3 text-sm text-muted-foreground">
            暂未生成任何 BERT 编码结果，请先运行一次媒体分析任务后再次查看。
          </p>
        </Card>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ArrowLeft } from 'lucide-vue-next'
import Button from '@/components/ui/Button.vue'
import Card from '@/components/ui/Card.vue'
import Badge from '@/components/ui/Badge.vue'
import ClusteringSummary from '@/components/beat/ClusteringSummary.vue'
import FieldSummaryTable from '@/components/beat/FieldSummaryTable.vue'
import FieldDetailPanel from '@/components/beat/FieldDetailPanel.vue'
import { getBeatEncodingRecord } from '@/api/events'

const router = useRouter()

const loading = ref(false)
const error = ref(null)
const recordData = ref(null)
const activeField = ref('')

const clusteringStats = computed(() => recordData.value?.last_clustering_stats || null)
const encodingMapping = computed(() => recordData.value?.encoding_mapping || {})

const rawFieldEntries = computed(() => clusteringStats.value?.fields || {})

const fieldList = computed(() => {
  const entries = rawFieldEntries.value
  if (!entries) return []
  return Object.entries(entries).map(([name, stats]) => {
    const before = stats.before_count ?? 0
    const after = stats.after_count ?? 0
    const reduction = stats.reduction ?? Math.max(0, before - after)
    const reductionRate = before ? (reduction / before) * 100 : 0
    const clusterCount = stats.total_clusters ?? stats.clusters?.length ?? 0
    const coverage = before ? ((stats.clustered_keywords ?? 0) / before) * 100 : 0
    return {
      name,
      label: name.replace(/_/g, ' '),
      before,
      after,
      reduction,
      reductionRate,
      reductionRateLabel: `${reductionRate.toFixed(1)}%`,
      reductionRateBar: `${Math.min(100, Math.max(0, reductionRate)).toFixed(1)}%`,
      clusterCount,
      clusterCoverageLabel: `${coverage.toFixed(1)}%`
    }
  }).sort((a, b) => {
    if (b.reductionRate !== a.reductionRate) {
      return b.reductionRate - a.reductionRate
    }
    return a.label.localeCompare(b.label, 'zh-CN')
  })
})

const totalKeywordsBefore = computed(() =>
  fieldList.value.reduce((sum, field) => sum + field.before, 0)
)

const totalKeywordsAfter = computed(() =>
  fieldList.value.reduce((sum, field) => sum + field.after, 0)
)

const totalReduction = computed(() => totalKeywordsBefore.value - totalKeywordsAfter.value)

const overallReductionRate = computed(() => {
  if (!totalKeywordsBefore.value) return 0
  return (totalReduction.value / totalKeywordsBefore.value) * 100
})

const totalClusters = computed(() => {
  const entries = rawFieldEntries.value
  if (!entries) return 0
  return Object.values(entries).reduce((sum, stats) => {
    if (typeof stats.total_clusters === 'number') return sum + stats.total_clusters
    return sum + (stats.clusters?.length ?? 0)
  }, 0)
})

const totalClusteredKeywords = computed(() => {
  const entries = rawFieldEntries.value
  if (!entries) return 0
  return Object.values(entries).reduce(
    (sum, stats) => sum + (stats.clustered_keywords ?? 0),
    0
  )
})

const summaryStats = computed(() => ({
  formattedTimestamp: formatDate(clusteringStats.value?.timestamp),
  fieldCount: fieldList.value.length,
  totalBefore: totalKeywordsBefore.value,
  totalAfter: totalKeywordsAfter.value,
  totalReduction: totalReduction.value,
  reductionRateLabel: `${overallReductionRate.value.toFixed(1)}%`,
  totalClusters: totalClusters.value,
  clusteredKeywords: totalClusteredKeywords.value
}))

const hasClusteringData = computed(() => fieldList.value.length > 0)

const activeFieldStats = computed(() =>
  rawFieldEntries.value?.[activeField.value] ?? null
)

const activeFieldMapping = computed(() =>
  encodingMapping.value?.[activeField.value] ?? {}
)

watch(
  fieldList,
  (fields) => {
    if (!fields.length) {
      activeField.value = ''
      return
    }
    if (!fields.some(field => field.name === activeField.value)) {
      activeField.value = fields[0].name
    }
  },
  { immediate: true }
)

const goBack = () => {
  router.back()
}

const handleFieldSelect = (fieldName) => {
  activeField.value = fieldName
}

const formatDate = (dateStr) => {
  if (!dateStr) return ''
  try {
    const date = new Date(dateStr)
    return date.toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    })
  } catch (error) {
    return dateStr
  }
}

const fetchBeatEncodingRecord = async () => {
  loading.value = true
  error.value = null
  try {
    const response = await getBeatEncodingRecord()
    if (response.success) {
      recordData.value = response.data
    } else {
      error.value = response.message || '获取数据失败'
    }
  } catch (err) {
    console.error('获取 BEAT 编码记录失败:', err)
    error.value = '获取数据失败，请稍后重试'
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchBeatEncodingRecord()
})
</script>

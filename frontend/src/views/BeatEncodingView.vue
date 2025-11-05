<template>
  <div class="min-h-screen bg-background">
    <!-- 头部导航 -->
    <header class="border-b bg-card">
      <div class="container mx-auto px-4 py-4">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-4">
            <Button variant="ghost" @click="goBack">
              <ArrowLeft class="mr-2 h-4 w-4" />
              返回
            </Button>
            <h1 class="text-2xl font-bold">BEAT编码器聚类效果</h1>
          </div>
          <Badge v-if="recordData" variant="outline">
            相似度阈值: {{ recordData.similarity_threshold }}
          </Badge>
        </div>
      </div>
    </header>

    <!-- 主内容 -->
    <main class="container mx-auto px-4 py-8">
      <!-- 加载状态 -->
      <div v-if="loading" class="flex justify-center items-center py-12">
        <div class="text-muted-foreground">加载中...</div>
      </div>

      <!-- 错误状态 -->
      <div v-else-if="error" class="flex justify-center items-center py-12">
        <Card class="p-6 max-w-md">
          <p class="text-destructive text-center">{{ error }}</p>
        </Card>
      </div>

      <!-- 数据展示 -->
      <div v-else-if="recordData" class="space-y-6">
        <!-- 统计概览 -->
        <Card v-if="clusteringStats" class="p-6">
          <h2 class="text-xl font-semibold mb-4">聚类统计概览</h2>
          <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <div class="space-y-2">
              <div class="text-sm text-muted-foreground">更新时间</div>
              <div class="text-lg font-semibold">
                {{ formatDate(clusteringStats.timestamp) }}
              </div>
            </div>
            <div class="space-y-2">
              <div class="text-sm text-muted-foreground">编码字段数</div>
              <div class="text-lg font-semibold">
                {{ Object.keys(clusteringStats.fields || {}).length }}
              </div>
            </div>
            <div class="space-y-2">
              <div class="text-sm text-muted-foreground">总编码关键词数</div>
              <div class="text-lg font-semibold">
                {{ totalKeywordsBefore }}
              </div>
            </div>
            <div class="space-y-2">
              <div class="text-sm text-muted-foreground">总聚类后数量</div>
              <div class="text-lg font-semibold text-primary">
                {{ totalKeywordsAfter }}
              </div>
            </div>
          </div>
        </Card>

        <!-- 各字段聚类统计图表 -->
        <div v-if="clusteringStats && clusteringStats.fields" class="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Card 
            v-for="(fieldStats, fieldName) in clusteringStats.fields" 
            :key="fieldName"
            class="p-6"
          >
                         <h3 class="text-lg font-semibold mb-4 capitalize">{{ fieldName.replace('_', ' ') }}</h3>
             <!-- 统计图表 -->
             <div 
               :ref="el => setChartRef(el, fieldName)" 
               :data-chart-field="fieldName"
               class="w-full h-64"
             ></div>
            <!-- 统计信息 -->
            <div class="mt-4 space-y-2">
              <div class="flex justify-between text-sm">
                <span class="text-muted-foreground">编码前:</span>
                <span class="font-semibold">{{ fieldStats.before_count }}</span>
              </div>
              <div class="flex justify-between text-sm">
                <span class="text-muted-foreground">编码后:</span>
                <span class="font-semibold text-primary">{{ fieldStats.after_count }}</span>
              </div>
              <div class="flex justify-between text-sm">
                <span class="text-muted-foreground">减少数量:</span>
                <span class="font-semibold text-green-600">{{ fieldStats.reduction }}</span>
              </div>
              <div class="flex justify-between text-sm">
                <span class="text-muted-foreground">减少率:</span>
                <span class="font-semibold text-green-600">
                  {{ fieldStats.reduction_rate.toFixed(1) }}%
                </span>
              </div>
            </div>
          </Card>
        </div>

        <!-- 相似性矩阵可视化 -->
        <Card v-if="clusteringStats && clusteringStats.fields" class="p-6">
          <h2 class="text-xl font-semibold mb-4">关键词相似性矩阵可视化</h2>
          <div class="space-y-6">
            <template 
              v-for="(fieldStats, fieldName) in clusteringStats.fields" 
              :key="fieldName"
            >
              <div 
                v-if="fieldStats && fieldStats.similarity_matrix && fieldStats.similarity_matrix.keywords && fieldStats.similarity_matrix.keywords.length > 0"
                class="space-y-4"
              >
                <div class="border-b pb-2">
                  <h3 class="text-lg font-medium capitalize">{{ fieldName.replace('_', ' ') }}</h3>
                </div>
                <!-- 相似性矩阵点图 -->
                <div 
                  :ref="el => setSimilarityChartRef(el, fieldName)" 
                  :data-similarity-field="fieldName"
                  class="w-full h-96 border rounded-lg"
                ></div>
              </div>
            </template>
            <div 
              v-if="!hasSimilarityMatrix" 
              class="text-center py-8 text-muted-foreground"
            >
              <p>暂无相似性矩阵数据</p>
            </div>
          </div>
        </Card>

        <!-- 聚类详情 -->
        <Card v-if="clusteringStats && clusteringStats.fields" class="p-6">
          <h2 class="text-xl font-semibold mb-4">聚类详情</h2>
          <div class="space-y-6">
            <div 
              v-for="(fieldStats, fieldName) in clusteringStats.fields" 
              :key="fieldName"
              class="space-y-4"
            >
              <div class="border-b pb-2">
                <h3 class="text-lg font-medium capitalize">{{ fieldName.replace('_', ' ') }}</h3>
              </div>
              <div 
                v-if="fieldStats.clusters && fieldStats.clusters.length > 0"
                class="grid grid-cols-1 md:grid-cols-2 gap-4"
              >
                <div
                  v-for="(cluster, index) in fieldStats.clusters"
                  :key="index"
                  class="border rounded-lg p-4 hover:border-primary/50 transition-colors"
                >
                  <div class="flex items-center justify-between mb-2">
                    <Badge variant="default" class="font-semibold">
                      {{ cluster.representative }}
                    </Badge>
                    <span class="text-xs text-muted-foreground">
                      {{ cluster.size }} 个关键词
                    </span>
                  </div>
                  <div class="flex flex-wrap gap-1 mt-2">
                    <Badge
                      v-for="member in cluster.members"
                      :key="member"
                      variant="outline"
                      class="text-xs"
                      :class="{ 'bg-primary/10': member === cluster.representative }"
                    >
                      {{ member }}
                    </Badge>
                  </div>
                </div>
              </div>
              <div v-else class="text-sm text-muted-foreground">
                该字段没有形成聚类（所有关键词都是唯一的）
              </div>
            </div>
          </div>
        </Card>

        <!-- 编码映射表 -->
        <Card v-if="encodingMapping && Object.keys(encodingMapping).length > 0" class="p-6">
          <h2 class="text-xl font-semibold mb-4">编码映射表</h2>
          <div class="space-y-6">
            <div
              v-for="(mappings, fieldName) in encodingMapping"
              :key="fieldName"
              class="space-y-2"
            >
              <h3 class="text-lg font-medium capitalize mb-3">
                {{ fieldName.replace('_', ' ') }}
                <span class="text-sm text-muted-foreground font-normal">
                  ({{ Object.keys(mappings).length }} 个映射)
                </span>
              </h3>
              <div class="border rounded-lg overflow-hidden">
                <div class="overflow-x-auto">
                  <table class="w-full text-sm">
                    <thead class="bg-muted/50">
                      <tr>
                        <th class="px-4 py-3 text-left font-semibold">原始关键词</th>
                        <th class="px-4 py-3 text-left font-semibold">→</th>
                        <th class="px-4 py-3 text-left font-semibold">编码后关键词</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr
                        v-for="(encoded, original) in mappings"
                        :key="original"
                        class="border-t hover:bg-muted/30 transition-colors"
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
            </div>
          </div>
        </Card>

        <!-- 无数据提示 -->
        <Card v-else class="p-6">
          <div class="text-center py-8">
            <p class="text-muted-foreground">
              暂无编码记录，请先运行一次媒体分析任务以生成编码数据
            </p>
          </div>
        </Card>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { ArrowLeft } from 'lucide-vue-next'
import * as echarts from 'echarts'
import Button from '@/components/ui/Button.vue'
import Card from '@/components/ui/Card.vue'
import Badge from '@/components/ui/Badge.vue'
import { getBeatEncodingRecord } from '@/api/events'

const router = useRouter()

const loading = ref(false)
const error = ref(null)
const recordData = ref(null)
const chartInstances = ref({})
const similarityChartInstances = ref({})

// 计算属性
const clusteringStats = computed(() => recordData.value?.last_clustering_stats)
const encodingMapping = computed(() => recordData.value?.encoding_mapping)

const totalKeywordsBefore = computed(() => {
  if (!clusteringStats.value?.fields) return 0
  return Object.values(clusteringStats.value.fields).reduce(
    (sum, field) => sum + (field.before_count || 0),
    0
  )
})

const totalKeywordsAfter = computed(() => {
  if (!clusteringStats.value?.fields) return 0
  return Object.values(clusteringStats.value.fields).reduce(
    (sum, field) => sum + (field.after_count || 0),
    0
  )
})

const hasSimilarityMatrix = computed(() => {
  if (!clusteringStats.value?.fields) return false
  return Object.values(clusteringStats.value.fields).some(
    field => field && field.similarity_matrix && 
             field.similarity_matrix.keywords && 
             field.similarity_matrix.keywords.length > 0
  )
})

// 设置图表引用
const setChartRef = (el, fieldName) => {
  if (el && !chartInstances.value[fieldName] && clusteringStats.value?.fields?.[fieldName]) {
    nextTick(() => {
      if (!chartInstances.value[fieldName]) { // 双重检查避免重复初始化
        initChart(el, fieldName)
      }
    })
  }
}

// 设置相似性图表引用
const setSimilarityChartRef = (el, fieldName) => {
  if (!el || !fieldName) return
  
  const fieldStats = clusteringStats.value?.fields?.[fieldName]
  if (!fieldStats || !fieldStats.similarity_matrix) return
  
  const similarityData = fieldStats.similarity_matrix
  if (!similarityData.keywords || !similarityData.matrix || similarityData.keywords.length === 0) return
  
  if (!similarityChartInstances.value[fieldName]) {
    nextTick(() => {
      if (!similarityChartInstances.value[fieldName]) {
        initSimilarityChart(el, fieldName)
      }
    })
  }
}

// 初始化图表
const initChart = (el, fieldName) => {
  if (!el || !clusteringStats.value?.fields?.[fieldName]) return
  
  const fieldStats = clusteringStats.value.fields[fieldName]
  const chart = echarts.init(el)
  chartInstances.value[fieldName] = chart

  const option = {
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'shadow'
      },
      formatter: function(params) {
        let result = params[0].name + '<br/>'
        params.forEach(param => {
          result += param.seriesName + ': ' + param.value + '<br/>'
          if (param.seriesName === '编码前' && params.length > 1) {
            const reduction = params[0].value - params[1].value
            const reductionRate = ((reduction / params[0].value) * 100).toFixed(1)
            result += '减少: ' + reduction + ' (' + reductionRate + '%)'
          }
        })
        return result
      }
    },
    legend: {
      data: ['编码前', '编码后']
    },
    grid: {
      left: '10%',
      right: '10%',
      bottom: '10%',
      top: '15%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: ['关键词数量']
    },
    yAxis: {
      type: 'value',
      name: '数量'
    },
    series: [
      {
        name: '编码前',
        type: 'bar',
        data: [fieldStats.before_count],
        itemStyle: {
          color: '#94a3b8',
          borderRadius: [4, 4, 0, 0]
        },
        label: {
          show: true,
          position: 'top',
          formatter: '{c}'
        }
      },
      {
        name: '编码后',
        type: 'bar',
        data: [fieldStats.after_count],
        itemStyle: {
          color: '#3b82f6',
          borderRadius: [4, 4, 0, 0]
        },
        label: {
          show: true,
          position: 'top',
          formatter: '{c}'
        }
      }
    ]
  }

  chart.setOption(option)

  // 响应式调整
  const resizeHandler = () => {
    chart.resize()
  }
  window.addEventListener('resize', resizeHandler)

  // 保存resize handler以便清理
  chart._resizeHandler = resizeHandler
}

// 初始化相似性矩阵图表（力导向图）
const initSimilarityChart = (el, fieldName) => {
  if (!el || !fieldName) return
  
  const fieldStats = clusteringStats.value?.fields?.[fieldName]
  if (!fieldStats || !fieldStats.similarity_matrix) return
  
  const similarityData = fieldStats.similarity_matrix
  if (!similarityData || !similarityData.keywords || !similarityData.matrix) return
  
  const keywords = similarityData.keywords
  const matrix = similarityData.matrix
  
  if (!Array.isArray(keywords) || !Array.isArray(matrix) || 
      keywords.length === 0 || matrix.length === 0 || 
      matrix.length !== keywords.length) {
    console.warn(`字段 ${fieldName} 的相似性矩阵数据不完整`)
    return
  }
  
  const chart = echarts.init(el)
  similarityChartInstances.value[fieldName] = chart
  
  // 创建节点
  const nodes = keywords.map((keyword, index) => ({
    id: index,
    name: keyword,
    value: keyword,
    symbolSize: 30,
    category: 0
  }))
  
  // 创建边（只连接相似度高的关键词对）
  const edges = []
  const similarityThreshold = 0.5  // 相似度阈值，只显示相似度大于0.5的连接
  
  for (let i = 0; i < matrix.length; i++) {
    for (let j = i + 1; j < matrix[i].length; j++) {
      const similarity = matrix[i][j]
      if (similarity >= similarityThreshold) {
        edges.push({
          source: i,
          target: j,
          value: similarity,
          lineStyle: {
            width: similarity * 3,  // 线的宽度表示相似度
            opacity: similarity
          }
        })
      }
    }
  }
  
  const option = {
    title: {
      text: '关键词相似性关系图',
      subtext: `相似度阈值: ${similarityThreshold}`,
      left: 'center',
      top: 10,
      textStyle: {
        fontSize: 14
      }
    },
    tooltip: {
      trigger: 'item',
      formatter: function(params) {
        if (params.dataType === 'node') {
          return `关键词: ${params.data.name}`
        } else if (params.dataType === 'edge') {
          const sourceName = keywords[params.data.source]
          const targetName = keywords[params.data.target]
          return `${sourceName} ↔ ${targetName}<br/>相似度: ${(params.data.value * 100).toFixed(1)}%`
        }
        return ''
      }
    },
    series: [
      {
        type: 'graph',
        layout: 'force',
        force: {
          repulsion: 1000,  // 节点之间的斥力
          gravity: 0.1,      // 向心力
          edgeLength: 150,   // 边的长度
          layoutAnimation: true
        },
        roam: true,  // 允许缩放和平移
        focusNodeAdjacency: true,  // 鼠标悬停时高亮相邻节点
        data: nodes,
        links: edges,
        categories: [{ name: '关键词' }],
        label: {
          show: true,
          position: 'right',
          formatter: '{b}',
          fontSize: 10
        },
        lineStyle: {
          color: 'source',
          curveness: 0.3
        },
        emphasis: {
          focus: 'adjacency',
          lineStyle: {
            width: 4
          }
        }
      }
    ]
  }
  
  chart.setOption(option)
  
  // 响应式调整
  const resizeHandler = () => {
    chart.resize()
  }
  window.addEventListener('resize', resizeHandler)
  
  // 保存resize handler以便清理
  chart._resizeHandler = resizeHandler
}

// 返回上一页
const goBack = () => {
  router.back()
}

// 格式化日期
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
  } catch (e) {
    return dateStr
  }
}

// 获取BEAT编码记录
const fetchBeatEncodingRecord = async () => {
  loading.value = true
  error.value = null
  try {
    const response = await getBeatEncodingRecord()
    
    if (response.success) {
      recordData.value = response.data
      
      // 等待DOM更新后初始化图表
      await nextTick()
      await nextTick() // 确保ref已经设置
      
      // 手动初始化所有图表
      if (clusteringStats.value?.fields) {
        Object.keys(clusteringStats.value.fields).forEach(fieldName => {
          const chartElement = document.querySelector(`[data-chart-field="${fieldName}"]`)
          if (chartElement && !chartInstances.value[fieldName]) {
            initChart(chartElement, fieldName)
          }
          
          // 初始化相似性图表
          const similarityElement = document.querySelector(`[data-similarity-field="${fieldName}"]`)
          if (similarityElement && !similarityChartInstances.value[fieldName]) {
            initSimilarityChart(similarityElement, fieldName)
          }
        })
      }
    } else {
      error.value = response.message || '获取数据失败'
    }
  } catch (err) {
    console.error('获取BEAT编码记录失败:', err)
    error.value = '获取数据失败，请稍后重试'
  } finally {
    loading.value = false
  }
}

// 清理图表实例
const cleanupCharts = () => {
  // 清理统计图表
  Object.values(chartInstances.value).forEach(chart => {
    if (chart && chart._resizeHandler) {
      window.removeEventListener('resize', chart._resizeHandler)
    }
    if (chart && typeof chart.dispose === 'function') {
      chart.dispose()
    }
  })
  chartInstances.value = {}
  
  // 清理相似性图表
  Object.values(similarityChartInstances.value).forEach(chart => {
    if (chart && chart._resizeHandler) {
      window.removeEventListener('resize', chart._resizeHandler)
    }
    if (chart && typeof chart.dispose === 'function') {
      chart.dispose()
    }
  })
  similarityChartInstances.value = {}
}

onMounted(() => {
  fetchBeatEncodingRecord()
})

onUnmounted(() => {
  cleanupCharts()
})
</script>

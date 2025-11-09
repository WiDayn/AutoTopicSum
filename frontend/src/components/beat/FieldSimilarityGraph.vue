<template>
  <div ref="chartRef" class="h-80 w-full rounded-lg border"></div>
</template>

<script setup>
import { nextTick, onBeforeUnmount, ref, watch } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  matrix: {
    type: Object,
    default: null
  },
  threshold: {
    type: Number,
    default: 0.5
  }
})

const chartRef = ref(null)
let chartInstance = null

const resizeHandler = () => {
  if (chartInstance) {
    chartInstance.resize()
  }
}

const disposeChart = () => {
  if (chartInstance) {
    window.removeEventListener('resize', resizeHandler)
    chartInstance.dispose()
    chartInstance = null
  }
}

const buildGraphOption = (keywords, matrix) => {
  const nodes = keywords.map((keyword, index) => ({
    id: index,
    name: keyword,
    symbolSize: 30,
    value: keyword,
    itemStyle: {
      color: '#3b82f6'
    },
    label: {
      fontSize: 11
    }
  }))

  const edges = []
  for (let i = 0; i < matrix.length; i++) {
    for (let j = i + 1; j < matrix[i].length; j++) {
      const similarity = matrix[i][j]
      if (similarity >= props.threshold) {
        edges.push({
          source: i,
          target: j,
          value: similarity,
          lineStyle: {
            width: 1 + similarity * 2,
            opacity: Math.min(0.9, similarity + 0.2)
          }
        })
      }
    }
  }

  return {
    tooltip: {
      trigger: 'item',
      formatter: (params) => {
        if (params.dataType === 'edge') {
          const from = keywords[params.data.source]
          const to = keywords[params.data.target]
          return `${from} ↔ ${to}<br/>相似度：${(params.data.value * 100).toFixed(1)}%`
        }
        return `关键词：${params.data.name}`
      }
    },
    series: [
      {
        type: 'graph',
        layout: 'force',
        roam: true,
        focusNodeAdjacency: true,
        force: {
          repulsion: 600,
          edgeLength: 140,
          friction: 0.2
        },
        data: nodes,
        links: edges,
        lineStyle: {
          color: '#94a3b8'
        }
      }
    ]
  }
}

const initChart = () => {
  const keywords = props.matrix?.keywords
  const matrixData = props.matrix?.matrix
  if (!chartRef.value || !Array.isArray(keywords) || !Array.isArray(matrixData)) {
    disposeChart()
    return
  }
  if (keywords.length <= 1 || matrixData.length !== keywords.length) {
    disposeChart()
    return
  }

  disposeChart()
  chartInstance = echarts.init(chartRef.value)
  chartInstance.setOption(buildGraphOption(keywords, matrixData))
  window.addEventListener('resize', resizeHandler)
}

watch(
  () => props.matrix,
  async () => {
    await nextTick()
    initChart()
  },
  { immediate: true, deep: true }
)

onBeforeUnmount(() => {
  disposeChart()
})
</script>


<template>
  <div ref="chartRef" class="h-52 w-full"></div>
</template>

<script setup>
import { nextTick, onBeforeUnmount, ref, watch } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  stats: {
    type: Object,
    default: null
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

const initChart = () => {
  if (!chartRef.value || !props.stats) return

  disposeChart()
  chartInstance = echarts.init(chartRef.value)
  chartInstance.setOption({
    grid: { left: 40, right: 20, top: 30, bottom: 30 },
    xAxis: {
      type: 'category',
      data: ['原始', '编码后'],
      axisTick: { show: false }
    },
    yAxis: {
      type: 'value',
      name: '关键词数'
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' }
    },
    series: [
      {
        type: 'bar',
        data: [
          props.stats.before_count ?? 0,
          props.stats.after_count ?? 0
        ],
        itemStyle: {
          color: (params) => (params.dataIndex === 0 ? '#94a3b8' : '#3b82f6'),
          borderRadius: [6, 6, 0, 0]
        },
        label: {
          show: true,
          position: 'top'
        }
      }
    ]
  })

  window.addEventListener('resize', resizeHandler)
}

watch(
  () => props.stats,
  async (stats) => {
    if (!stats) {
      disposeChart()
      return
    }
    await nextTick()
    initChart()
  },
  { immediate: true }
)

onBeforeUnmount(() => {
  disposeChart()
})
</script>


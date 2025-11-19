<template>
  <div class="sentiment-analysis">
    <div class="analysis-section">
      <h3>新闻情感分析</h3>
      
      <!-- 输入区域 -->
      <div class="input-section">
        <el-input
          type="textarea"
          :rows="4"
          placeholder="输入新闻标题或内容进行情感分析..."
          v-model="inputText"
          resize="none"
        ></el-input>
        <el-button 
          type="primary" 
          @click="handleAnalyze" 
          :loading="analyzing"
          style="margin-top: 10px;"
        >
          <el-icon><Search /></el-icon>
          分析情感
        </el-button>
      </div>
      
      <!-- 结果显示 -->
      <div class="result-section" v-if="currentResult">
        <el-divider></el-divider>
        <h4>分析结果</h4>
        <div class="result-display">
          <div class="sentiment-badge" :class="currentResult.sentiment">
            {{ sentimentLabels[currentResult.sentiment] }}
          </div>
          <div class="confidence">
            置信度: {{ (currentResult.confidence * 100).toFixed(1) }}%
          </div>
        </div>
        
        <!-- 情感分布图表 -->
        <div class="chart-section">
          <h5>情感分布</h5>
          <div class="chart-container">
            <canvas ref="sentimentChart" width="400" height="200"></canvas>
          </div>
        </div>
      </div>
    </div>
    
    <!-- 情感趋势 -->
    <div class="trend-section" v-if="trendData.length > 0">
      <el-divider></el-divider>
      <h4>情感趋势分析</h4>
      <div class="trend-chart-container">
        <canvas ref="trendChart" width="600" height="300"></canvas>
      </div>
    </div>

    <!-- 情感统计 -->
    <div class="stats-section" v-if="statsData">
      <el-divider></el-divider>
      <h4>情感统计</h4>
      <el-row :gutter="20">
        <el-col :span="8">
          <div class="stat-card positive">
            <div class="stat-value">{{ statsData.positive || 0 }}</div>
            <div class="stat-label">积极</div>
          </div>
        </el-col>
        <el-col :span="8">
          <div class="stat-card neutral">
            <div class="stat-value">{{ statsData.neutral || 0 }}</div>
            <div class="stat-label">中性</div>
          </div>
        </el-col>
        <el-col :span="8">
          <div class="stat-card negative">
            <div class="stat-value">{{ statsData.negative || 0 }}</div>
            <div class="stat-label">负面</div>
          </div>
        </el-col>
      </el-row>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { ElMessage } from 'element-plus'
import { Search } from '@element-plus/icons-vue'
import { analyzeText, getSentimentTrend, getSentimentStats } from '@/api/sentiment'
import Chart from 'chart.js/auto'

// 响应式数据
const inputText = ref('')
const analyzing = ref(false)
const currentResult = ref(null)
const trendData = ref([])
const statsData = ref(null)
const sentimentChart = ref(null)
const trendChart = ref(null)

const sentimentLabels = {
  positive: '积极',
  neutral: '中性',
  negative: '负面'
}

// 图表实例
let sentimentChartInstance = null
let trendChartInstance = null

onMounted(() => {
  loadTrendData()
  loadStatsData()
})

onBeforeUnmount(() => {
  if (sentimentChartInstance) {
    sentimentChartInstance.destroy()
  }
  if (trendChartInstance) {
    trendChartInstance.destroy()
  }
})

const handleAnalyze = async () => {
  if (!inputText.value.trim()) {
    ElMessage.warning('请输入要分析的文本')
    return
  }
  
  analyzing.value = true
  try {
    const response = await analyzeText(inputText.value)
    currentResult.value = response
    ElMessage.success('分析完成')
    
    // 渲染图表
    renderSentimentChart()
    
    // 重新加载趋势和统计数据
    loadTrendData()
    loadStatsData()
  } catch (error) {
    console.error('情感分析失败:', error)
    ElMessage.error('分析失败，请重试')
  } finally {
    analyzing.value = false
  }
}

const loadTrendData = async () => {
  try {
    const response = await getSentimentTrend()
    trendData.value = response.recent_data || []
    if (trendData.value.length > 0) {
      renderTrendChart()
    }
  } catch (error) {
    console.error('加载趋势数据失败:', error)
  }
}

const loadStatsData = async () => {
  try {
    const response = await getSentimentStats()
    statsData.value = response
  } catch (error) {
    console.error('加载统计数据失败:', error)
  }
}

const renderSentimentChart = () => {
  if (!currentResult.value) return
  
  const ctx = sentimentChart.value.getContext('2d')
  
  if (sentimentChartInstance) {
    sentimentChartInstance.destroy()
  }
  
  sentimentChartInstance = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: ['积极', '中性', '负面'],
      datasets: [{
        data: [
          currentResult.value.scores.positive,
          currentResult.value.scores.neutral,
          currentResult.value.scores.negative
        ],
        backgroundColor: ['#67C23A', '#E6A23C', '#F56C6C'],
        borderWidth: 2,
        borderColor: '#fff'
      }]
    },
    options: {
      responsive: true,
      plugins: {
        legend: {
          position: 'bottom'
        },
        tooltip: {
          callbacks: {
            label: function(context) {
              const value = context.parsed
              return `${context.label}: ${(value * 100).toFixed(1)}%`
            }
          }
        }
      }
    }
  })
}

const renderTrendChart = () => {
  if (trendData.value.length === 0) return
  
  const ctx = trendChart.value.getContext('2d')
  
  if (trendChartInstance) {
    trendChartInstance.destroy()
  }
  
  // 准备趋势数据
  const labels = trendData.value.map(item => 
    new Date(item.timestamp).toLocaleTimeString()
  )
  
  trendChartInstance = new Chart(ctx, {
    type: 'line',
    data: {
      labels: labels,
      datasets: [
        {
          label: '积极',
          data: trendData.value.map(item => item.scores.positive),
          borderColor: '#67C23A',
          backgroundColor: 'rgba(103, 194, 58, 0.1)',
          tension: 0.4,
          fill: true
        },
        {
          label: '中性',
          data: trendData.value.map(item => item.scores.neutral),
          borderColor: '#E6A23C',
          backgroundColor: 'rgba(230, 162, 60, 0.1)',
          tension: 0.4,
          fill: true
        },
        {
          label: '负面',
          data: trendData.value.map(item => item.scores.negative),
          borderColor: '#F56C6C',
          backgroundColor: 'rgba(245, 108, 108, 0.1)',
          tension: 0.4,
          fill: true
        }
      ]
    },
    options: {
      responsive: true,
      scales: {
        y: {
          beginAtZero: true,
          max: 1,
          ticks: {
            callback: function(value) {
              return (value * 100) + '%'
            }
          }
        }
      },
      plugins: {
        tooltip: {
          callbacks: {
            label: function(context) {
              return `${context.dataset.label}: ${(context.parsed.y * 100).toFixed(1)}%`
            }
          }
        }
      }
    }
  })
}
</script>

<style scoped>
.sentiment-analysis {
  padding: 20px;
}

.input-section {
  margin-bottom: 20px;
}

.result-display {
  display: flex;
  align-items: center;
  gap: 15px;
  margin: 15px 0;
}

.sentiment-badge {
  padding: 8px 16px;
  border-radius: 20px;
  font-weight: bold;
  color: white;
  font-size: 16px;
}

.sentiment-badge.positive {
  background-color: #67C23A;
}

.sentiment-badge.neutral {
  background-color: #E6A23C;
}

.sentiment-badge.negative {
  background-color: #F56C6C;
}

.confidence {
  color: #606266;
  font-size: 14px;
}

.chart-section, .trend-section, .stats-section {
  margin-top: 20px;
}

.chart-container {
  max-width: 400px;
  margin: 0 auto;
}

.trend-chart-container {
  max-width: 600px;
  margin: 0 auto;
}

.stat-card {
  text-align: center;
  padding: 20px;
  border-radius: 8px;
  color: white;
  font-weight: bold;
}

.stat-card.positive {
  background: linear-gradient(135deg, #67C23A, #85ce61);
}

.stat-card.neutral {
  background: linear-gradient(135deg, #E6A23C, #ebb563);
}

.stat-card.negative {
  background: linear-gradient(135deg, #F56C6C, #f78989);
}

.stat-value {
  font-size: 32px;
  margin-bottom: 8px;
}

.stat-label {
  font-size: 16px;
  opacity: 0.9;
}
</style>
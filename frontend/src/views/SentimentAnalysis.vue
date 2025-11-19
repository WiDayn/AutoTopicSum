<template>
  <div class="sentiment-analysis-page">
    <el-card>
      <template #header>
        <div class="page-header">
          <h2>新闻情感分析</h2>
          <p class="page-description">分析新闻内容的情感倾向，查看情感趋势图表</p>
        </div>
      </template>
      
      <SentimentAnalysis />
    </el-card>
  </div>
</template>

<script setup>
import SentimentAnalysis from '@/components/beat/SentimentAnalysis.vue'
</script>

<style scoped>
.sentiment-analysis-page {
  padding: 20px;
}

.page-header {
  text-align: center;
}

.page-header h2 {
  margin: 0;
  color: #303133;
}

.page-description {
  margin: 8px 0 0 0;
  color: #909399;
  font-size: 14px;
}
</style>
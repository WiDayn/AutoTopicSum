import request from '@/lib/request'  // 修改导入路径

// 分析单个文本情感
export function analyzeText(text) {
  return request({
    url: '/sentiment/analyze',
    method: 'post',
    data: {
      text: text
    }
  })
}

// 批量分析新闻情感
export function analyzeNewsList(newsList) {
  return request({
    url: '/sentiment/analyze-news',
    method: 'post',
    data: {
      news_list: newsList
    }
  })
}

// 获取情感趋势
export function getSentimentTrend() {
  return request({
    url: '/sentiment/trend',
    method: 'get'
  })
}

// 获取分析历史
export function getAnalysisHistory() {
  return request({
    url: '/sentiment/history',
    method: 'get'
  })
}

// 获取情感统计
export function getSentimentStats() {
  return request({
    url: '/sentiment/stats',
    method: 'get'
  })
}
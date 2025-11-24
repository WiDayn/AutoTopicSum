import apiClient from './client'

/**
 * 分词接口
 * @param {string} text - 待分词的文本
 */
export const segmentText = (text) => {
  return apiClient.post('/word-segmentation', { text })
}

/**
 * 批量分词接口
 * @param {Array<string>} texts - 待分词的文本列表
 */
export const batchSegmentText = (texts) => {
  return apiClient.post('/word-segmentation/batch', { texts })
}


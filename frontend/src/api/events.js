import apiClient from './client'

/**
 * 提交搜索任务（异步）
 */
export const submitSearchTask = (data) => {
  return apiClient.post('/events/search', data)
}

/**
 * 获取事件列表（包括处理中的）
 */
export const getEvents = (params) => {
  return apiClient.get('/events', { params })
}

/**
 * 获取事件详情
 */
export const getEventDetail = (eventId) => {
  return apiClient.get(`/events/${eventId}`)
}

/**
 * 获取任务状态
 */
export const getTaskStatus = (taskId) => {
  return apiClient.get(`/tasks/${taskId}`)
}

/**
 * 获取BEAT编码记录
 */
export const getBeatEncodingRecord = () => {
  return apiClient.get('/beat/encoding-record')
}


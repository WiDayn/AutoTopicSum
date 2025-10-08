import apiClient from './client'

/**
 * 搜索事件
 */
export const searchEvents = (params) => {
  return apiClient.get('/events/search', { params })
}

/**
 * 获取事件列表
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


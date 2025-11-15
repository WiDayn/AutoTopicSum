import { createRouter, createWebHistory } from 'vue-router'
import SearchView from '@/views/SearchView.vue'

const routes = [
  {
    path: '/',
    name: 'search',
    component: SearchView
  },
  {
    path: '/event/:id',
    name: 'event-detail',
    component: () => import('@/views/EventDetailView.vue')
  },
  {
    path: '/bert-encoding',
    name: 'bert-encoding',
    component: () => import('@/views/BertEncodingView.vue')
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router


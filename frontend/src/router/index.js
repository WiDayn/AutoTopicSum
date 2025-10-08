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
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router


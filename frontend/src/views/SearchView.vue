<template>
  <div class="min-h-screen">
    <!-- 头部 -->
    <header class="border-b">
      <div class="container mx-auto px-4 py-6">
        <div class="flex items-center justify-between mb-6">
          <h1 class="text-3xl font-bold">新闻聚合引擎</h1>
          <Button variant="outline" @click="goToBeatEncoding">
            <BarChart3 class="mr-2 h-4 w-4" />
            BEAT编码器媒体分类聚类效果
          </Button>
        </div>
        <SearchBar v-model="searchQuery" @search="handleSearch" />
      </div>
    </header>

    <!-- 主内容区 -->
    <main class="container mx-auto px-4 py-8">
      <!-- 加载状态 -->
      <div v-if="loading" class="flex justify-center items-center py-12">
        <div class="text-muted-foreground">加载中...</div>
      </div>

      <!-- 事件列表 -->
      <div v-else-if="events.length > 0" class="space-y-4">
        <div class="flex items-center justify-between mb-4">
          <div>
            <p class="text-muted-foreground">
              <template v-if="searchQuery">
                搜索 "<span class="font-semibold text-foreground">{{ searchQuery }}</span>" 找到 {{ total }} 个相关事件
              </template>
              <template v-else>
                共 {{ total }} 个事件
              </template>
            </p>
          </div>
          <Button 
            v-if="searchQuery" 
            variant="ghost" 
            size="sm" 
            @click="clearSearch"
          >
            清除搜索
          </Button>
        </div>
        
        <EventCard
          v-for="event in events"
          :key="event.id"
          :event="event"
          @click="goToDetail(event.id)"
        />

        <!-- 分页 -->
        <div v-if="totalPages > 1" class="flex justify-center gap-2 mt-8">
          <Button
            variant="outline"
            :disabled="currentPage === 1"
            @click="changePage(currentPage - 1)"
          >
            上一页
          </Button>
          <span class="flex items-center px-4">
            第 {{ currentPage }} / {{ totalPages }} 页
          </span>
          <Button
            variant="outline"
            :disabled="currentPage === totalPages"
            @click="changePage(currentPage + 1)"
          >
            下一页
          </Button>
        </div>
      </div>

      <!-- 空状态 -->
      <div v-else class="text-center py-12">
        <div class="max-w-md mx-auto">
          <div class="text-6xl mb-4">🔍</div>
          <p class="text-muted-foreground text-lg mb-2">
            <template v-if="searchQuery && hasSearched">
              未找到关于 "{{ searchQuery }}" 的相关事件
            </template>
            <template v-else-if="hasSearched">
              暂无缓存的事件
            </template>
            <template v-else>
              欢迎使用新闻聚合引擎
            </template>
          </p>
          <p class="text-sm text-muted-foreground mb-4">
            <template v-if="!hasSearched">
              在上方搜索框输入关键词，即可从多个数据源聚合新闻
            </template>
            <template v-else-if="searchQuery">
              试试其他关键词吧
            </template>
            <template v-else>
              请搜索关键词来获取相关新闻事件
            </template>
          </p>
          <div class="flex gap-2 justify-center">
            <Button 
              v-if="searchQuery && hasSearched" 
              variant="outline"
              @click="clearSearch"
            >
              清除搜索
            </Button>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { BarChart3 } from 'lucide-vue-next'
import SearchBar from '@/components/SearchBar.vue'
import EventCard from '@/components/EventCard.vue'
import Button from '@/components/ui/Button.vue'
import { submitSearchTask, getEvents } from '@/api/events'

const router = useRouter()

const loading = ref(false)
const events = ref([])
const total = ref(0)
const currentPage = ref(1)
const totalPages = ref(1)
const perPage = ref(10)
const searchQuery = ref('')
const hasSearched = ref(false)  // 记录是否已经搜索过
const pollingInterval = ref(null)  // 轮询定时器

// 搜索事件
const handleSearch = async (query) => {
  if (!query || !query.trim()) {
    // 如果搜索词为空，显示所有事件
    searchQuery.value = ''
  } else {
    searchQuery.value = query.trim()
  }
  currentPage.value = 1
  hasSearched.value = true
  
  // 提交搜索任务
  if (searchQuery.value) {
    await submitSearch(searchQuery.value)
  } else {
    await fetchEvents()
  }
}

// 提交搜索任务
const submitSearch = async (query) => {
  loading.value = true
  try {
    const response = await submitSearchTask({
      query: query,
      language: 'zh-CN',
      region: 'CN'
    })
    
    if (response.success) {
      console.log('任务已提交:', response.data)
      // 立即获取事件列表（包含新提交的处理中的事件）
      await fetchEvents()
      // 开始轮询更新
      startPolling()
    }
  } catch (error) {
    console.error('提交搜索任务失败:', error)
  } finally {
    loading.value = false
  }
}

// 清除搜索
const clearSearch = () => {
  searchQuery.value = ''
  currentPage.value = 1
  hasSearched.value = true
  fetchEvents()
}

// 切换页码
const changePage = async (page) => {
  currentPage.value = page
  await fetchEvents()
}

// 获取事件列表
const fetchEvents = async () => {
  try {
    const response = await getEvents()
    
    if (response.success && response.data) {
      events.value = response.data.events
      total.value = response.data.total
      totalPages.value = 1
      
      // 检查是否还有处理中的任务
      const hasProcessing = events.value.some(e => e.status === 'processing')
      if (!hasProcessing && pollingInterval.value) {
        // 没有处理中的任务，停止轮询
        stopPolling()
      }
    }
  } catch (error) {
    console.error('获取事件列表失败:', error)
    events.value = []
    total.value = 0
  }
}

// 开始轮询
const startPolling = () => {
  // 清除现有定时器
  if (pollingInterval.value) {
    clearInterval(pollingInterval.value)
  }
  
  // 每2秒更新一次
  pollingInterval.value = setInterval(() => {
    fetchEvents()
  }, 2000)
}

// 停止轮询
const stopPolling = () => {
  if (pollingInterval.value) {
    clearInterval(pollingInterval.value)
    pollingInterval.value = null
  }
}

// 跳转到详情页
const goToDetail = (id) => {
  router.push({ name: 'event-detail', params: { id } })
}

// 跳转到BEAT编码页面
const goToBeatEncoding = () => {
  router.push({ name: 'beat-encoding' })
}

// 初始加载
onMounted(async () => {
  // 初始加载时获取已缓存的事件列表
  await fetchEvents()
  // 开始轮询（如果有处理中的任务）
  const hasProcessing = events.value.some(e => e.status === 'processing')
  if (hasProcessing) {
    startPolling()
  }
})

// 组件卸载时清理
onUnmounted(() => {
  stopPolling()
})
</script>


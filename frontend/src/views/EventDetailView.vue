<template>
  <div class="min-h-screen">
    <!-- 头部导航 -->
    <header class="border-b">
      <div class="container mx-auto px-4 py-4">
        <Button variant="ghost" @click="goBack">
          <ArrowLeft class="mr-2 h-4 w-4" />
          返回
        </Button>
      </div>
    </header>

    <!-- 主内容 -->
    <main class="container mx-auto px-4 py-8">
      <!-- 加载状态 -->
      <div v-if="loading" class="flex justify-center items-center py-12">
        <div class="text-muted-foreground">加载中...</div>
      </div>

      <!-- 事件详情 -->
      <div v-else-if="event" class="max-w-4xl mx-auto space-y-6">
        <!-- 标题和元信息 -->
        <div class="space-y-4">
          <div class="flex items-center gap-2">
            <Badge v-if="event.category" variant="secondary">
              {{ event.category }}
            </Badge>
          </div>
          <h1 class="text-4xl font-bold">{{ event.title }}</h1>
          <div class="flex items-center gap-4 text-muted-foreground">
            <div class="flex items-center gap-1">
              <Calendar class="h-4 w-4" />
              <span>{{ event.date }}</span>
            </div>
          </div>
        </div>

        <!-- 摘要 -->
        <Card class="p-6">
          <h2 class="text-xl font-semibold mb-3">事件摘要</h2>
          <p class="text-muted-foreground leading-relaxed">{{ event.summary }}</p>
        </Card>

        <!-- 详细内容 -->
        <Card class="p-6">
          <h2 class="text-xl font-semibold mb-3">详细内容</h2>
          <p class="text-muted-foreground leading-relaxed whitespace-pre-line">
            {{ event.content }}
          </p>
        </Card>

        <!-- 标签 -->
        <div v-if="event.tags && event.tags.length" class="flex gap-2 flex-wrap">
          <Badge v-for="tag in event.tags" :key="tag" variant="outline">
            {{ tag }}
          </Badge>
        </div>

        <!-- 来源文章 -->
        <Card class="p-6">
          <h2 class="text-xl font-semibold mb-4">来源文章</h2>
          <div class="space-y-3">
            <div
              v-for="source in event.sources"
              :key="source.id"
              class="border-l-2 border-primary pl-4 py-2"
            >
              <a
                :href="source.url"
                target="_blank"
                rel="noopener noreferrer"
                class="text-primary hover:underline font-medium"
              >
                {{ source.title }}
              </a>
              <p class="text-sm text-muted-foreground mt-1">
                发布时间：{{ source.published_at }}
              </p>
            </div>
          </div>
        </Card>
      </div>

      <!-- 错误状态 -->
      <div v-else class="text-center py-12">
        <p class="text-muted-foreground text-lg">事件不存在或已被删除</p>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ArrowLeft, Calendar } from 'lucide-vue-next'
import Button from '@/components/ui/Button.vue'
import Card from '@/components/ui/Card.vue'
import Badge from '@/components/ui/Badge.vue'
import { getEventDetail } from '@/api/events'

const router = useRouter()
const route = useRoute()

const loading = ref(false)
const event = ref(null)

// 返回上一页
const goBack = () => {
  router.back()
}

// 获取事件详情
const fetchEventDetail = async () => {
  loading.value = true
  try {
    const eventId = route.params.id
    const response = await getEventDetail(eventId)
    
    if (response.success) {
      event.value = response.data
    }
  } catch (error) {
    console.error('获取事件详情失败:', error)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchEventDetail()
})
</script>


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

        <!-- 媒体分析概览 -->
        <Card v-if="event.media_analysis && event.media_analysis.total_media > 0" class="p-6">
          <div 
            class="flex items-center justify-between cursor-pointer"
            @click="showMediaOverview = !showMediaOverview"
          >
            <h2 class="text-xl font-semibold">
              媒体分析概览
              <span class="text-muted-foreground font-normal text-base">
                (共分析 {{ event.media_analysis.total_media }} 个媒体)
              </span>
            </h2>
            <Button variant="ghost" size="sm">
              <ChevronDown 
                class="h-5 w-5 transition-transform duration-200"
                :class="{ 'rotate-180': showMediaOverview }"
              />
            </Button>
          </div>
          
          <div 
            v-show="showMediaOverview"
            class="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4"
          >
            <div
              v-for="(mediaInfo, mediaName) in event.media_analysis.media_info"
              :key="mediaName"
              class="border rounded-lg p-3 space-y-2 hover:border-primary/50 transition-colors"
            >
              <h3 class="font-semibold text-sm">{{ mediaName }}</h3>
              <div class="space-y-1">
                <div v-if="mediaInfo.category" class="flex gap-1 flex-wrap">
                  <Badge 
                    v-for="tag in splitTags(mediaInfo.category)" 
                    :key="tag" 
                    variant="default"
                    class="text-xs"
                  >
                    {{ tag }}
                  </Badge>
                </div>
                <div v-if="mediaInfo.content_domain" class="flex gap-1 flex-wrap">
                  <Badge 
                    v-for="tag in splitTags(mediaInfo.content_domain)" 
                    :key="tag" 
                    variant="secondary"
                    class="text-xs"
                  >
                    {{ tag }}
                  </Badge>
                </div>
                <div v-if="mediaInfo.political_stance" class="text-xs text-muted-foreground">
                  立场：{{ mediaInfo.political_stance }}
                </div>
              </div>
            </div>
          </div>
        </Card>

        <!-- 来源文章 -->
        <Card class="p-6">
          <h2 class="text-xl font-semibold mb-4">
            来源文章
            <span v-if="event.source_count" class="text-muted-foreground font-normal text-base">
              (共 {{ event.source_count }} 篇)
            </span>
          </h2>
          <div class="space-y-6">
            <div
              v-for="(source, index) in event.sources"
              :key="index"
              class="border-l-2 border-primary pl-4 py-2 space-y-3"
            >
              <!-- 文章标题和链接 -->
              <div>
                <a
                  :href="source.url"
                  target="_blank"
                  rel="noopener noreferrer"
                  class="text-primary hover:underline font-medium text-lg"
                >
                  {{ source.title }}
                </a>
                <p class="text-sm text-muted-foreground mt-1">
                  来源：{{ source.source }} • {{ formatDate(source.published_at) }}
                </p>
                <p class="text-sm mt-1" :class="source.filter ? 'text-red-500' : 'text-green-500'">
                  是否被过滤：{{ source.filter ? '是' : '否' }}
                </p>
              </div>

              <!-- 媒体信息 -->
              <div v-if="source.media_info" class="bg-secondary/30 rounded-lg p-4 space-y-2">
                <h4 class="text-sm font-semibold text-muted-foreground mb-2">媒体信息</h4>
                
                <!-- 媒体类别 -->
                <div v-if="source.media_info.category" class="flex items-start gap-2">
                  <span class="text-xs text-muted-foreground min-w-[60px]">类别：</span>
                  <div class="flex gap-1 flex-wrap">
                    <Badge 
                      v-for="tag in splitTags(source.media_info.category)" 
                      :key="tag" 
                      variant="default"
                      class="text-xs"
                    >
                      {{ tag }}
                    </Badge>
                  </div>
                </div>

                <!-- 内容领域 -->
                <div v-if="source.media_info.content_domain" class="flex items-start gap-2">
                  <span class="text-xs text-muted-foreground min-w-[60px]">领域：</span>
                  <div class="flex gap-1 flex-wrap">
                    <Badge 
                      v-for="tag in splitTags(source.media_info.content_domain)" 
                      :key="tag" 
                      variant="secondary"
                      class="text-xs"
                    >
                      {{ tag }}
                    </Badge>
                  </div>
                </div>

                <!-- 政治立场 -->
                <div v-if="source.media_info.political_stance" class="flex items-start gap-2">
                  <span class="text-xs text-muted-foreground min-w-[60px]">立场：</span>
                  <div class="flex gap-1 flex-wrap">
                    <Badge 
                      v-for="tag in splitTags(source.media_info.political_stance)" 
                      :key="tag" 
                      variant="outline"
                      class="text-xs"
                    >
                      {{ tag }}
                    </Badge>
                  </div>
                </div>

                <!-- 地理位置 -->
                <div v-if="source.media_info.location" class="flex items-start gap-2">
                  <span class="text-xs text-muted-foreground min-w-[60px]">位置：</span>
                  <div class="flex gap-1 flex-wrap">
                    <Badge 
                      v-for="tag in splitTags(source.media_info.location)" 
                      :key="tag" 
                      variant="outline"
                      class="text-xs"
                    >
                      {{ tag }}
                    </Badge>
                  </div>
                </div>

                <!-- 其他信息 -->
                <div class="grid grid-cols-1 md:grid-cols-2 gap-2 pt-2 border-t border-border/50">
                  <div v-if="source.media_info.ownership" class="text-xs">
                    <span class="text-muted-foreground">所有制：</span>
                    <span class="ml-1">{{ source.media_info.ownership }}</span>
                  </div>
                  <div v-if="source.media_info.funding" class="text-xs">
                    <span class="text-muted-foreground">资金来源：</span>
                    <span class="ml-1">{{ source.media_info.funding }}</span>
                  </div>
                  <div v-if="source.media_info.target_audience" class="text-xs md:col-span-2">
                    <span class="text-muted-foreground">目标受众：</span>
                    <span class="ml-1">{{ source.media_info.target_audience }}</span>
                  </div>
                </div>
              </div>
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
import { ArrowLeft, Calendar, ChevronDown } from 'lucide-vue-next'
import Button from '@/components/ui/Button.vue'
import Card from '@/components/ui/Card.vue'
import Badge from '@/components/ui/Badge.vue'
import { getEventDetail } from '@/api/events'

const router = useRouter()
const route = useRoute()

const loading = ref(false)
const event = ref(null)
const showMediaOverview = ref(false)  // 默认折叠状态

// 返回上一页
const goBack = () => {
  router.back()
}

// 分割标签（用/分隔）
const splitTags = (text) => {
  if (!text) return []
  return text.split('/').map(tag => tag.trim()).filter(tag => tag.length > 0)
}

// 格式化日期
const formatDate = (dateStr) => {
  if (!dateStr) return ''
  try {
    const date = new Date(dateStr)
    return date.toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    })
  } catch (e) {
    return dateStr
  }
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


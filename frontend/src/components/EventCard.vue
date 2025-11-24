<template>
  <Card class="p-6 hover:shadow-md transition-shadow cursor-pointer" @click="handleClick">
    <div class="space-y-3">
      <div class="flex items-start justify-between">
        <h3 class="text-xl font-semibold">{{ event.title }}</h3>
        <div class="flex gap-2">
          <!-- 状态标识 -->
          <Badge v-if="event.status === 'processing'" variant="default" class="animate-pulse">
            处理中
          </Badge>
          <Badge v-else-if="event.status === 'failed'" variant="destructive">
            失败
          </Badge>
          <Badge v-if="event.category && event.status !== 'processing'" variant="secondary">
            {{ event.category }}
          </Badge>
        </div>
      </div>
      
      <!-- 进度条（处理中时显示） -->
      <div v-if="event.status === 'processing' && event.progress" class="space-y-2">
        <div class="flex items-center justify-between text-sm">
          <div class="flex flex-col gap-1">
            <span class="text-muted-foreground font-medium">
              {{ event.progress.message || '正在处理...' }}
            </span>
          </div>
          <span class="text-muted-foreground font-semibold" v-if="event.progress.total > 0">
            {{ progressPercent }}%
          </span>
        </div>
        <div class="w-full bg-secondary rounded-full h-2.5 overflow-hidden">
          <div 
            class="bg-primary h-full transition-all duration-500 ease-out"
            :style="{ width: progressPercent + '%' }"
          ></div>
        </div>
      </div>
      
      <!-- 摘要 -->
      <p v-if="event.summary" class="text-muted-foreground line-clamp-2">
        {{ event.summary }}
      </p>
      <p v-else-if="event.status === 'processing'" class="text-muted-foreground italic">
        正在从多个数据源聚合新闻...
      </p>
      
      <!-- 分词结果（简要） -->
      <div v-if="event.word_segmentation && event.status !== 'processing'" class="flex flex-wrap gap-1.5 items-center">
        <div
          v-for="(segment, index) in event.word_segmentation.segments.slice(0, 5)"
          :key="index"
          class="flex items-center gap-1"
          :title="segment.pos_label || segment.pos || ''"
        >
          <Badge
            variant="outline"
            class="text-xs"
          >
            {{ segment.word }}
          </Badge>
          <span v-if="segment.pos" class="text-xs text-muted-foreground">
            ({{ segment.pos }})
          </span>
        </div>
        <span v-if="event.word_segmentation.segments.length > 5" class="text-xs text-muted-foreground">
          +{{ event.word_segmentation.segments.length - 5 }}
        </span>
      </div>

      <!-- 元信息 -->
      <div v-if="event.status !== 'processing'" class="space-y-2">
        <div class="flex items-center gap-4 text-sm text-muted-foreground">
          <div class="flex items-center gap-1">
            <Calendar class="h-4 w-4" />
            <span>{{ formatDate(event.date) }}</span>
          </div>
          <div class="flex items-center gap-1">
            <FileText class="h-4 w-4" />
            <span>{{ event.source_count }} 个来源</span>
          </div>
          <div v-if="event.media_analysis && event.media_analysis.total_media > 0" class="flex items-center gap-1">
            <span class="text-xs">📊 {{ event.media_analysis.total_media }} 个媒体已分析</span>
          </div>
        </div>
      </div>
    </div>
  </Card>
</template>

<script setup>
import { computed } from 'vue'
import { Calendar, FileText } from 'lucide-vue-next'
import Card from './ui/Card.vue'
import Badge from './ui/Badge.vue'

const props = defineProps({
  event: {
    type: Object,
    required: true
  }
})

const emit = defineEmits(['click'])

// 计算进度百分比
const progressPercent = computed(() => {
  if (!props.event.progress || !props.event.progress.total) {
    return 0
  }
  return Math.round((props.event.progress.current / props.event.progress.total) * 100)
})

// 格式化日期
const formatDate = (dateStr) => {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  return date.toLocaleDateString('zh-CN')
}

const handleClick = () => {
  // 处理中的事件不允许点击进入详情
  if (props.event.status !== 'processing') {
    emit('click')
  }
}
</script>


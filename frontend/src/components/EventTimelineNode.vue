<template>
  <li class="mb-10 ms-6">            
    <span class="absolute flex items-center justify-center w-7 h-7 rounded-md bg-blue-200 shadow-lg -start-3.5">
      <CalendarDays size="18"/>
    </span>
    <time class="bg-gray-50 border border-default-medium text-heading text-sm font-medium px-2 py-1 rounded">
      {{ formatDate(node.timestamp) }}
    </time>
    <h3 class="flex items-center mb-1 text-lg font-semibold text-heading my-2">
      {{ node.key_event }}
    </h3>
    <p v-if="node.summary" class="text-gray-500">
      {{ node.summary }}
    </p>
    <div class="h-fit w-fit border-l-2 border-sky-500 pl-2 mb-2 mt-4">
      <p class="font-semibold text-heading">相关新闻</p>
    </div>
    <div class="flex flex-wrap gap-2">
      <div v-for="(article, index) in node.source_articles" :key="index">
        <Button
        asChild
        variant="outline"
        size="sm"
        class="h-auto py-1 px-3"
        >
          <a class="flex gap-2 items-center" :href="article.url" target="_blank" rel="noopener noreferrer">
            <ExternalLink size="16"/>
            <span class="inline-block max-w-[20rem] truncate">
              {{ article.title || '未知标题' }}
            </span>
          </a>
        </Button>
      </div>
    </div>
  </li>
</template>

<script setup>
import Button from '@/components/ui/Button.vue'
import { CalendarDays, ExternalLink } from 'lucide-vue-next';

defineProps({
  // nodes: { timestamp, key_event_title, summary, source_articles }
  node: {
    type: Object,
    required: true
  },
})

const formatDate = (dateStr) => {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleString('zh-CN')
}
</script>
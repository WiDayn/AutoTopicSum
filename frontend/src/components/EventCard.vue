<template>
  <Card class="p-6 hover:shadow-md transition-shadow cursor-pointer" @click="handleClick">
    <div class="space-y-3">
      <div class="flex items-start justify-between">
        <h3 class="text-xl font-semibold">{{ event.title }}</h3>
        <Badge v-if="event.category" variant="secondary">
          {{ event.category }}
        </Badge>
      </div>
      
      <p class="text-muted-foreground line-clamp-2">
        {{ event.summary }}
      </p>
      
      <div class="flex items-center gap-4 text-sm text-muted-foreground">
        <div class="flex items-center gap-1">
          <Calendar class="h-4 w-4" />
          <span>{{ event.date }}</span>
        </div>
        <div class="flex items-center gap-1">
          <FileText class="h-4 w-4" />
          <span>{{ event.source_count }} 个来源</span>
        </div>
      </div>
    </div>
  </Card>
</template>

<script setup>
import { Calendar, FileText } from 'lucide-vue-next'
import Card from './ui/Card.vue'
import Badge from './ui/Badge.vue'

defineProps({
  event: {
    type: Object,
    required: true
  }
})

const emit = defineEmits(['click'])

const handleClick = () => {
  emit('click')
}
</script>


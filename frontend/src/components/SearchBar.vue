<template>
  <div class="w-full max-w-3xl mx-auto">
    <div class="flex gap-2">
      <div class="relative flex-1">
        <Input
          v-model="localQuery"
          placeholder="输入关键词搜索新闻事件..."
          class="flex-1 pr-10"
          @keyup.enter="handleSearch"
          @input="handleInput"
        />
        <button
          v-if="localQuery"
          @click="clearSearch"
          class="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
          type="button"
        >
          <X class="h-4 w-4" />
        </button>
      </div>
      <Button @click="handleSearch" :disabled="!localQuery.trim()">
        <Search class="mr-2 h-4 w-4" />
        搜索
      </Button>
    </div>

    <!-- 分词结果显示 -->
    <div v-if="segmentationResult && localQuery.trim()" class="mt-3 p-3 bg-muted/50 rounded-lg border">
      <div class="flex items-center justify-between mb-2">
        <span class="text-sm font-medium text-foreground">分词结果：</span>
        <span v-if="segmentationLoading" class="text-xs text-muted-foreground">分词中...</span>
        <span v-else class="text-xs text-muted-foreground">
          {{ segmentationResult.total_words }} 个词
        </span>
      </div>
      <div class="flex flex-wrap gap-2">
        <div
          v-for="(segment, index) in segmentationResult.segments"
          :key="index"
          class="flex flex-col items-center gap-1"
          :title="segment.pos_label || segment.pos || ''"
        >
          <span class="inline-flex items-center px-2 py-1 rounded-md bg-background border text-sm">
            {{ segment.word }}
          </span>
          <span v-if="segment.pos" class="text-xs text-muted-foreground">
            {{ segment.pos }}
          </span>
          <span v-if="segment.pos_label" class="text-xs text-muted-foreground">
            {{ segment.pos_label }}
          </span>
        </div>
      </div>
      <div v-if="segmentationResult.segmented_text_with_pos" class="mt-2 text-xs text-muted-foreground">
        完整分词（含词性）：{{ segmentationResult.segmented_text_with_pos }}
      </div>
      <div v-else-if="segmentationResult.segmented_text" class="mt-2 text-xs text-muted-foreground">
        完整分词：{{ segmentationResult.segmented_text }}
      </div>
    </div>

    <p v-if="localQuery && !segmentationResult" class="text-xs text-muted-foreground mt-2">
      按 Enter 键快速搜索
    </p>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { Search, X } from 'lucide-vue-next'
import Input from './ui/Input.vue'
import Button from './ui/Button.vue'
import { segmentText } from '@/api/wordSegmentation'

const props = defineProps({
  modelValue: {
    type: String,
    default: ''
  }
})

const emit = defineEmits(['update:modelValue', 'search'])

// 使用计算属性实现双向绑定
const localQuery = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value)
})

// 分词相关状态
const segmentationResult = ref(null)
const segmentationLoading = ref(false)
let debounceTimer = null

// 处理输入变化，进行分词
const handleInput = () => {
  if (debounceTimer) {
    clearTimeout(debounceTimer)
  }

  if (!localQuery.value || !localQuery.value.trim()) {
    segmentationResult.value = null
    return
  }

  debounceTimer = setTimeout(async () => {
    await performSegmentation(localQuery.value.trim())
  }, 500)
}

// 执行分词
const performSegmentation = async (text) => {
  if (!text || !text.trim()) {
    segmentationResult.value = null
    return
  }

  segmentationLoading.value = true
  try {
    const response = await segmentText(text)
    if (response.success && response.data) {
      segmentationResult.value = response.data
    } else {
      segmentationResult.value = null
    }
  } catch (error) {
    console.error('分词失败:', error)
    segmentationResult.value = null
  } finally {
    segmentationLoading.value = false
  }
}

const handleSearch = () => {
  if (localQuery.value.trim()) {
    emit('search', localQuery.value)
  }
}

const clearSearch = () => {
  localQuery.value = ''
  segmentationResult.value = null
  if (debounceTimer) {
    clearTimeout(debounceTimer)
  }
  // 清除后也触发搜索，显示所有事件
  emit('search', '')
}

// 监听外部传入的modelValue变化
watch(() => props.modelValue, (newValue) => {
  if (!newValue || !newValue.trim()) {
    segmentationResult.value = null
  } else {
    if (debounceTimer) {
      clearTimeout(debounceTimer)
    }
    debounceTimer = setTimeout(async () => {
      await performSegmentation(newValue.trim())
    }, 500)
  }
})
</script>


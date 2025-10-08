<template>
  <div class="w-full max-w-3xl mx-auto">
    <div class="flex gap-2">
      <div class="relative flex-1">
        <Input
          v-model="localQuery"
          placeholder="输入关键词搜索新闻事件..."
          class="flex-1 pr-10"
          @keyup.enter="handleSearch"
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
    <p v-if="localQuery" class="text-xs text-muted-foreground mt-2">
      按 Enter 键快速搜索
    </p>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Search, X } from 'lucide-vue-next'
import Input from './ui/Input.vue'
import Button from './ui/Button.vue'

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

const handleSearch = () => {
  if (localQuery.value.trim()) {
    emit('search', localQuery.value)
  }
}

const clearSearch = () => {
  localQuery.value = ''
  // 清除后也触发搜索，显示所有事件
  emit('search', '')
}
</script>


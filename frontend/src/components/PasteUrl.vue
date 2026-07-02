<template>
  <div class="paste-url">
    <input
      v-model="url"
      type="text"
      placeholder="粘贴视频/音频链接（B站、抖音、小红书等）"
      :disabled="submitting"
      @keydown.enter="submit"
    />
    <button @click="submit" :disabled="submitting || !url.trim()">
      {{ submitting ? '处理中...' : '提交' }}
    </button>
    <p v-if="error" class="error">{{ error }}</p>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useTasksStore } from '@/stores/tasks'

const emit = defineEmits<{ submitted: [taskId: number] }>()
const tasksStore = useTasksStore()
const url = ref('')
const submitting = ref(false)
const error = ref('')

async function submit() {
  if (!url.value.trim()) return
  submitting.value = true
  error.value = ''
  try {
    const taskId = await tasksStore.createFromUrl(url.value.trim())
    url.value = ''
    emit('submitted', taskId)
  } catch (e: any) {
    error.value = e.response?.data?.detail || e.message || '提交失败'
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.paste-url { display: flex; gap: 0.5rem; }
.paste-url input {
  flex: 1; padding: 0.5rem 0.75rem; border-radius: 6px;
  border: 1px solid #333; background: #16213e; color: #e0e0e0; font-size: 0.9rem;
}
.paste-url input:focus { outline: none; border-color: #4fc3f7; }
.paste-url button {
  padding: 0.5rem 1rem; border: none; border-radius: 6px;
  background: #4fc3f7; color: #000; font-size: 0.9rem; font-weight: 600; cursor: pointer;
}
.paste-url button:disabled { opacity: 0.6; cursor: not-allowed; }
.error { color: #ef5350; font-size: 0.75rem; }
</style>

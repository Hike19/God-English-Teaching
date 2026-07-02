<template>
  <div class="import-upload">
    <button @click="triggerUpload" :disabled="uploading">
      {{ uploading ? statusText : '📁 导入素材库' }}
    </button>
    <div v-if="uploading" class="progress-wrap">
      <div class="progress-bar">
        <div class="progress-fill" :style="{ width: progress + '%' }" />
      </div>
      <span class="progress-pct">{{ progress }}%</span>
    </div>
    <input
      ref="fileInput"
      type="file"
      accept=".mp3,.mp4,.wav,.webm,.m4a,.flac"
      @change="handleFile"
      hidden
    />
    <p v-if="error" class="error">{{ error }}</p>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useTasksStore } from '@/stores/tasks'

const emit = defineEmits<{ uploaded: [taskId: number] }>()
const tasksStore = useTasksStore()
const fileInput = ref<HTMLInputElement>()
const uploading = ref(false)
const error = ref('')
const progress = ref(0)
const processing = ref(false)

const statusText = computed(() => {
  if (processing.value) return '处理中...'
  if (progress.value === 100) return '处理中...'
  return `上传中 ${progress.value}%`
})

function triggerUpload() {
  fileInput.value?.click()
}

async function handleFile(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return

  uploading.value = true
  error.value = ''
  progress.value = 0
  processing.value = false
  try {
    const taskId = await tasksStore.createFromFile(file, (pct) => {
      progress.value = pct
      if (pct === 100) processing.value = true
    })
    emit('uploaded', taskId)
  } catch (e: any) {
    error.value = e.response?.data?.detail || e.message || '上传失败'
  } finally {
    uploading.value = false
    progress.value = 0
    processing.value = false
    if (fileInput.value) fileInput.value.value = ''
  }
}
</script>

<style scoped>
.import-upload button {
  padding: 0.5rem 1rem; border: none; border-radius: 6px;
  background: #1a73e8; color: white; font-size: 0.9rem; cursor: pointer;
}
.import-upload button:disabled { opacity: 0.6; cursor: not-allowed; }
.progress-wrap { display: flex; align-items: center; gap: 0.5rem; margin-top: 0.25rem; }
.progress-bar { flex: 1; height: 4px; background: #333; border-radius: 2px; }
.progress-fill { height: 100%; background: #4fc3f7; border-radius: 2px; transition: width 0.2s; }
.progress-pct { font-size: 0.7rem; color: #999; min-width: 2.5rem; }
.error { color: #ef5350; font-size: 0.75rem; margin-top: 0.25rem; }
</style>

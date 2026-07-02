<template>
  <div class="import-upload">
    <button @click="triggerUpload" :disabled="uploading">
      {{ uploading ? '上传中...' : '📁 导入素材库' }}
    </button>
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
import { ref } from 'vue'
import { useTasksStore } from '@/stores/tasks'

const emit = defineEmits<{ uploaded: [taskId: number] }>()
const tasksStore = useTasksStore()
const fileInput = ref<HTMLInputElement>()
const uploading = ref(false)
const error = ref('')

function triggerUpload() {
  fileInput.value?.click()
}

async function handleFile(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return

  uploading.value = true
  error.value = ''
  try {
    const taskId = await tasksStore.createFromFile(file)
    emit('uploaded', taskId)
  } catch (e: any) {
    error.value = e.response?.data?.detail || e.message || '上传失败'
  } finally {
    uploading.value = false
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
.error { color: #ef5350; font-size: 0.75rem; margin-top: 0.25rem; }
</style>

<template>
  <div class="modal-overlay" @click.self="$emit('close')">
    <div class="modal">
      <h2>反馈</h2>
      <textarea
        v-model="content"
        placeholder="请输入您的反馈或建议..."
        rows="5"
        maxlength="2000"
      />
      <p class="char-count">{{ content.length }}/2000</p>
      <p v-if="error" class="error">{{ error }}</p>
      <p v-if="success" class="success">感谢您的反馈！</p>
      <div class="actions">
        <button @click="$emit('close')">取消</button>
        <button class="primary" @click="submit" :disabled="submitting || !content.trim()">
          {{ submitting ? '提交中...' : '提交' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { submitFeedback } from '@/api/feedback'

defineEmits<{ close: [] }>()

const content = ref('')
const submitting = ref(false)
const error = ref('')
const success = ref(false)

async function submit() {
  if (!content.value.trim()) return
  submitting.value = true
  error.value = ''
  try {
    await submitFeedback(content.value.trim())
    success.value = true
    setTimeout(() => { success.value = false }, 2000)
    content.value = ''
  } catch (e: any) {
    error.value = e.response?.data?.detail || '提交失败'
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.modal-overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,0.6);
  display: flex; align-items: center; justify-content: center; z-index: 1000;
}
.modal {
  background: #1a1a2e; border-radius: 12px; padding: 2rem;
  width: 400px;
}
h2 { margin-bottom: 1rem; color: #e0e0e0; }
textarea {
  width: 100%; padding: 0.75rem; border-radius: 8px;
  border: 1px solid #333; background: #16213e; color: #e0e0e0;
  font-size: 1rem; resize: vertical;
}
textarea:focus { outline: none; border-color: #4fc3f7; }
.char-count { text-align: right; font-size: 0.75rem; color: #666; margin-top: 0.25rem; }
.error { color: #ef5350; font-size: 0.875rem; margin-top: 0.5rem; }
.success { color: #66bb6a; font-size: 0.875rem; margin-top: 0.5rem; }
.actions { display: flex; justify-content: flex-end; gap: 0.75rem; margin-top: 1rem; }
.actions button {
  padding: 0.5rem 1.25rem; border: none; border-radius: 6px;
  font-size: 0.9rem; cursor: pointer;
}
.actions button:first-child { background: #333; color: #e0e0e0; }
.actions button.primary { background: #4fc3f7; color: #000; font-weight: 600; }
.actions button:disabled { opacity: 0.6; cursor: not-allowed; }
</style>

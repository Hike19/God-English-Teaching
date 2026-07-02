<template>
  <div class="modal-overlay" @click.self="$emit('close')">
    <div class="modal">
      <h2>{{ isLogin ? '登录' : '注册' }}</h2>
      <form @submit.prevent="handleSubmit">
        <input v-model="username" type="text" placeholder="用户名" required minlength="2" />
        <input v-model="password" type="password" placeholder="密码" required minlength="6" />
        <p v-if="error" class="error">{{ error }}</p>
        <button type="submit" :disabled="loading">
          {{ loading ? '...' : isLogin ? '登录' : '注册' }}
        </button>
      </form>
      <p class="toggle">
        {{ isLogin ? '还没有账号？' : '已有账号？' }}
        <a href="#" @click.prevent="isLogin = !isLogin; error = ''">
          {{ isLogin ? '去注册' : '去登录' }}
        </a>
      </p>
      <button class="close-btn" @click="$emit('close')">✕</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useAuthStore } from '@/stores/auth'

defineEmits<{ close: [] }>()

const auth = useAuthStore()
const isLogin = ref(true)
const username = ref('')
const password = ref('')
const loading = ref(false)
const error = ref('')

async function handleSubmit() {
  loading.value = true
  error.value = ''
  try {
    if (isLogin.value) {
      await auth.loginAction(username.value, password.value)
    } else {
      await auth.registerAction(username.value, password.value)
    }
    username.value = ''
    password.value = ''
  } catch (e: any) {
    error.value = e.response?.data?.detail || '操作失败，请重试'
  } finally {
    loading.value = false
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
  width: 360px; position: relative;
}
h2 { text-align: center; margin-bottom: 1.5rem; color: #e0e0e0; }
input {
  display: block; width: 100%; margin-bottom: 0.75rem;
  padding: 0.75rem; border-radius: 8px; border: 1px solid #333;
  background: #16213e; color: #e0e0e0; font-size: 1rem;
}
input:focus { outline: none; border-color: #4fc3f7; }
button[type="submit"] {
  width: 100%; padding: 0.75rem; border: none; border-radius: 8px;
  background: #4fc3f7; color: #000; font-size: 1rem; font-weight: 600; cursor: pointer;
}
button[type="submit"]:disabled { opacity: 0.6; cursor: not-allowed; }
.error { color: #ef5350; font-size: 0.875rem; margin-bottom: 0.5rem; }
.toggle { text-align: center; margin-top: 1rem; font-size: 0.875rem; color: #999; }
.toggle a { color: #4fc3f7; text-decoration: none; }
.close-btn {
  position: absolute; top: 0.75rem; right: 0.75rem;
  background: none; border: none; color: #999; font-size: 1.25rem; cursor: pointer;
}
</style>

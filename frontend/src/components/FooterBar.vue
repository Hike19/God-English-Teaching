<template>
  <footer class="footer-bar">
    <button @click="$emit('login')">
      {{ auth.isLoggedIn ? auth.user?.username : '登录' }}
    </button>
    <button v-if="auth.isLoggedIn" @click="auth.logout()">退出</button>
    <button @click="$emit('feedback')">反馈</button>
  </footer>
</template>

<script setup lang="ts">
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
defineEmits<{ login: []; feedback: [] }>()
</script>

<style scoped>
.footer-bar {
  display: flex; justify-content: center; gap: 1rem;
  padding: 0.75rem 1.5rem; background: #1a1a2e; border-top: 1px solid #333;
}
.footer-bar button {
  padding: 0.5rem 1rem; border: 1px solid #333; border-radius: 6px;
  background: transparent; color: #999; font-size: 0.85rem; cursor: pointer;
}
.footer-bar button:hover { color: #e0e0e0; border-color: #666; }
</style>
